"""
Knowledge Graph Builder
=======================
Builds and maintains the org knowledge graph from ingested resources.

Two phases :
  1. Structure   — nodes from resources/chunks (documents, tables, folders)
                   edges from connector hierarchy (CONTAINS, REFERENCES)
  2. NLP Extract — entities from chunk content via OpenAI
                   (persons, concepts, topics) + MENTIONS edges

Triggered as a Celery background task after ingestion completes.
"""

import logging
import os
from datetime import datetime, timezone
from uuid import UUID
from openai import OpenAI
import json

from config.extensions import db
from models.knowledge_graph import KGNode, KGEdge
from models.resource import Resource, ResourceChunk
from models.connector import Connector
from services.encryption_service import EncryptionService

logger = logging.getLogger(__name__)
openai_client = OpenAI()
encryption_service = EncryptionService()

EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", "1536"))


# =============================================================================
# CELERY TASK ENTRY POINT
# =============================================================================

def build_kg_for_org(org_id: str) -> dict:
    """
    Main entry point — builds the full KG for an org.
    Called as a Celery task after ingestion completes.
    """
    logger.info(f"Building Knowledge Graph for org {org_id}")
    builder = KnowledgeGraphBuilder(org_id)

    # Phase 1 — Structure
    struct_result = builder.build_structure()

    # Phase 2 — NLP Entity extraction
    nlp_result = builder.extract_entities()

    result = {
        'nodes_created': struct_result['nodes_created'],
        'edges_created': struct_result['edges_created'],
        'entities_extracted': nlp_result['entities_extracted'],
        'mentions_created': nlp_result['mentions_created'],
    }

    logger.info(f"KG build complete for org {org_id}: {result}")
    return result


# =============================================================================
# BUILDER CLASS
# =============================================================================

class KnowledgeGraphBuilder:

    def __init__(self, org_id: str):
        self.org_id = org_id
        self._node_cache: dict[str, KGNode] = {}

    # =========================================================================
    # PHASE 1 — STRUCTURE
    # =========================================================================

    def build_structure(self) -> dict:
        """
        Build structural nodes and edges from resources.
        Documents, tables, folders + CONTAINS/REFERENCES edges.
        """
        nodes_created = 0
        edges_created = 0

        resources = Resource.query.filter_by(
            organization_id=self.org_id,
            ingestion_status='done',
            deleted_at=None
        ).all()

        # Group by connector
        by_connector: dict[str, list[Resource]] = {}
        for r in resources:
            key = str(r.connector_id)
            by_connector.setdefault(key, []).append(r)

        for connector_id, connector_resources in by_connector.items():
            connector = Connector.query.get(UUID(connector_id))
            if not connector:
                continue

            # Create connector root node
            root_node = self._upsert_node(
                node_type='connector',
                external_id=f"connector:{connector_id}",
                connector_type=connector.type,
                name=connector.name,
                metadata={'connector_id': connector_id, 'type': connector.type}
            )
            nodes_created += 1

            for resource in connector_resources:
                # Determine node type
                if connector.type == 'sql':
                    node_type = 'table'
                else:
                    meta = resource.ressource_metadata or {}
                    mime = meta.get('type', '')
                    if 'folder' in mime.lower():
                        node_type = 'folder'
                    else:
                        node_type = 'document'

                # Create resource node
                resource_node = self._upsert_node(
                    node_type=node_type,
                    external_id=f"resource:{resource.id}",
                    connector_type=connector.type,
                    name=resource.title or 'Untitled',
                    metadata={
                        'resource_id': str(resource.id),
                        'external_id': resource.external_id,
                        'connector_id': connector_id,
                        **({
                            'link': resource.ressource_metadata.get('link'),
                            'size': resource.ressource_metadata.get('size'),
                            'modified': resource.ressource_metadata.get('modified'),
                        } if resource.ressource_metadata else {})
                    },
                    text_for_embedding=resource.title
                )
                nodes_created += 1

                # Edge: connector CONTAINS resource
                edge = self._upsert_edge(root_node, resource_node, 'CONTAINS')
                if edge:
                    edges_created += 1

                # SQL — detect FK relationships between tables
                if connector.type == 'sql':
                    edges_created += self._build_sql_references(
                        resource, resource_node, connector_resources
                    )

        db.session.commit()
        logger.info(f"Structure phase: {nodes_created} nodes, {edges_created} edges")
        return {'nodes_created': nodes_created, 'edges_created': edges_created}

    def _build_sql_references(
        self,
        resource: Resource,
        resource_node: KGNode,
        all_resources: list[Resource]
    ) -> int:
        """Detect FK relationships from column names (heuristic)."""
        edges_created = 0
        meta = resource.ressource_metadata or {}
        columns = []

        # Extract columns from chunk metadata
        chunks = ResourceChunk.query.filter_by(
            resource_id=resource.id
        ).first()
        if chunks and chunks.chunk_metadata:
            columns = chunks.chunk_metadata.get('columns', [])

        table_names = {r.title: r for r in all_resources}

        for col in columns:
            col_name = col.get('name', '') if isinstance(col, dict) else str(col)
            if col_name.endswith('_id'):
                referenced_table = col_name[:-3]
                if referenced_table in table_names:
                    ref_resource = table_names[referenced_table]
                    ref_node = self._get_node(f"resource:{ref_resource.id}")
                    if ref_node:
                        edge = self._upsert_edge(
                            resource_node, ref_node, 'REFERENCES',
                            metadata={'via_column': col_name}
                        )
                        if edge:
                            edges_created += 1

        return edges_created

    # =========================================================================
    # PHASE 2 — NLP ENTITY EXTRACTION
    # =========================================================================

    def extract_entities(self) -> dict:
        """
        Extract named entities (persons, concepts, topics) from chunk content
        using OpenAI, then create nodes + MENTIONS edges.
        """
        entities_extracted = 0
        mentions_created = 0

        # Get all chunks for this org that haven't been processed yet
        chunks = ResourceChunk.query.filter_by(
            organization_id=self.org_id
        ).filter(
            ResourceChunk.chunk_type.in_(['text', 'title'])
        ).limit(500).all()  # process max 500 chunks per run

        # Group chunks by resource to batch OpenAI calls
        by_resource: dict[str, list[ResourceChunk]] = {}
        for chunk in chunks:
            key = str(chunk.resource_id)
            by_resource.setdefault(key, []).append(chunk)

        for resource_id, resource_chunks in by_resource.items():
            resource_node = self._get_node(f"resource:{resource_id}")
            if not resource_node:
                continue

            # Combine first 3 chunks for context (avoid too many tokens)
            combined_text = '\n'.join(
                c.content for c in resource_chunks[:3]
            )[:3000]  # max 3000 chars

            try:
                entities = self._extract_entities_from_text(combined_text)

                for entity in entities:
                    entity_type = entity.get('type', 'concept').lower()
                    entity_name = entity.get('name', '').strip()

                    if not entity_name or len(entity_name) < 2:
                        continue

                    # Upsert entity node
                    entity_node = self._upsert_node(
                        node_type=entity_type,
                        external_id=f"entity:{self.org_id}:{entity_type}:{entity_name.lower()}",
                        connector_type=None,
                        name=entity_name,
                        metadata={
                            'entity_type': entity_type,
                            'org_id': self.org_id,
                        },
                        text_for_embedding=entity_name
                    )
                    entities_extracted += 1

                    # Edge: resource MENTIONS entity
                    edge = self._upsert_edge(
                        resource_node, entity_node, 'MENTIONS',
                        metadata={'confidence': entity.get('confidence', 1.0)}
                    )
                    if edge:
                        mentions_created += 1

            except Exception as e:
                logger.warning(f"Entity extraction failed for resource {resource_id}: {e}")
                continue

        db.session.commit()
        logger.info(f"NLP phase: {entities_extracted} entities, {mentions_created} mentions")
        return {
            'entities_extracted': entities_extracted,
            'mentions_created': mentions_created
        }

    def _extract_entities_from_text(self, text: str) -> list[dict]:
        """
        Extract named entities using OpenAI.
        Returns list of {name, type, confidence} dicts.
        """
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a named entity extractor. "
                        "Extract key entities from the text and return ONLY a JSON array. "
                        "Each item must have: name (string), type (one of: person, organization, "
                        "concept, topic, location, product), confidence (0.0-1.0). "
                        "Return max 10 most important entities. "
                        "Return ONLY the JSON array, no other text."
                    )
                },
                {
                    "role": "user",
                    "content": f"Extract entities from:\n\n{text}"
                }
            ],
            temperature=0,
            max_tokens=500,
        )

        raw = response.choices[0].message.content.strip()

        # Strip markdown code blocks if present
        if raw.startswith('```'):
            raw = raw.split('```')[1]
            if raw.startswith('json'):
                raw = raw[4:]
        raw = raw.strip()

        entities = json.loads(raw)
        return entities if isinstance(entities, list) else []

    # =========================================================================
    # QUERY API — used by agents
    # =========================================================================

    def semantic_search(
        self,
        query: str,
        node_types: list[str] = None,
        limit: int = 10
    ) -> list[KGNode]:
        """Find nodes semantically similar to query."""
        query_embedding = self._embed(query)

        q = KGNode.query.filter_by(org_id=self.org_id)
        if node_types:
            q = q.filter(KGNode.node_type.in_(node_types))

        results = q.filter(
            KGNode.embedding.isnot(None)
        ).order_by(
            KGNode.embedding.cosine_distance(query_embedding)
        ).limit(limit).all()

        return results

    def get_neighbors(
        self,
        node_id: str,
        relation: str = None
    ) -> list[KGNode]:
        """Get all nodes connected to a given node."""
        q = KGEdge.query.filter_by(org_id=self.org_id, source_id=node_id)
        if relation:
            q = q.filter_by(relation=relation)
        edges = q.all()
        return [e.target_node for e in edges]

    def find_by_name(
        self,
        name: str,
        node_type: str = None
    ) -> list[KGNode]:
        """Find nodes by name (fuzzy)."""
        q = KGNode.query.filter_by(org_id=self.org_id).filter(
            KGNode.name.ilike(f'%{name}%')
        )
        if node_type:
            q = q.filter_by(node_type=node_type)
        return q.limit(20).all()

    # =========================================================================
    # INTERNAL HELPERS
    # =========================================================================

    def _upsert_node(
        self,
        node_type: str,
        external_id: str,
        connector_type: str,
        name: str,
        metadata: dict = None,
        text_for_embedding: str = None,
    ) -> KGNode:
        """Create or update a node."""
        # Check cache first
        if external_id in self._node_cache:
            return self._node_cache[external_id]

        existing = KGNode.query.filter_by(
            org_id=self.org_id,
            external_id=external_id
        ).first()

        embedding = self._embed(text_for_embedding or name)

        if existing:
            existing.name = name
            existing.metadata = metadata
            existing.embedding = embedding
            existing.updated_at = datetime.now(timezone.utc)
            self._node_cache[external_id] = existing
            return existing

        node = KGNode(
            org_id=self.org_id,
            node_type=node_type,
            external_id=external_id,
            connector_type=connector_type,
            name=name,
            metadata=metadata,
            embedding=embedding,
        )
        db.session.add(node)
        db.session.flush()
        self._node_cache[external_id] = node
        return node

    def _upsert_edge(
        self,
        source: KGNode,
        target: KGNode,
        relation: str,
        metadata: dict = None,
        weight: float = 1.0
    ) -> KGEdge | None:
        """Create or update an edge."""
        existing = KGEdge.query.filter_by(
            org_id=self.org_id,
            source_id=source.id,
            target_id=target.id,
            relation=relation
        ).first()

        if existing:
            existing.weight = weight
            existing.metadata = metadata
            return None  # already exists, not new

        edge = KGEdge(
            org_id=self.org_id,
            source_id=source.id,
            target_id=target.id,
            relation=relation,
            weight=weight,
            metadata=metadata,
        )
        db.session.add(edge)
        return edge

    def _get_node(self, external_id: str) -> KGNode | None:
        """Get a node from cache or DB."""
        if external_id in self._node_cache:
            return self._node_cache[external_id]
        node = KGNode.query.filter_by(
            org_id=self.org_id,
            external_id=external_id
        ).first()
        if node:
            self._node_cache[external_id] = node
        return node

    def _embed(self, text: str) -> list[float]:
        """Generate embedding using OpenAI."""
        if not text:
            return None
        text = text[:8000]
        response = openai_client.embeddings.create(
            model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
            input=text,
            dimensions=EMBEDDING_DIMENSIONS,
        )
        return response.data[0].embedding