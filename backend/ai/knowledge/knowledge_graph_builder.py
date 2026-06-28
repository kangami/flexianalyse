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

# NLP entity extraction tuning
MENTION_CHUNK_TYPES = ('text', 'title')
KG_CHUNKS_PER_RUN   = int(os.getenv("KG_CHUNKS_PER_RUN", "1500"))  # safety cap per build
# One chat/completions call is made PER window, so bigger windows = far fewer
# LLM calls. gpt-4o-mini has a large context, so we pack much more per call.
KG_WINDOW_CHARS     = int(os.getenv("KG_WINDOW_CHARS", "12000"))
# Phase-2 NLP entity extraction is the dominant LLM cost — allow disabling it
# entirely (the structural KG + live Text-to-SQL still work without it).
KG_ENABLE_ENTITY_EXTRACTION = os.getenv(
    "KG_ENTITY_EXTRACTION", "true"
).lower() in ("1", "true", "yes")


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

    # Phase 2 — NLP Entity extraction (optional; the main per-window LLM cost)
    if KG_ENABLE_ENTITY_EXTRACTION:
        nlp_result = builder.extract_entities()
    else:
        logger.info("NLP entity extraction disabled (KG_ENTITY_EXTRACTION=false)")
        nlp_result = {'entities_extracted': 0, 'mentions_created': 0}

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
        # Cache embeddings by text within a single build — entity names repeat a
        # lot across windows/documents, so this avoids re-embedding duplicates.
        self._embed_cache: dict[str, list[float]] = {}

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

        # Pre-embed every resource title in batch so the per-node _upsert_node
        # calls below hit the cache instead of one embeddings request per node.
        self._embed_many([r.title or 'Untitled' for r in resources])

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

        Incremental: only chunks whose ``kg_processed_at`` is NULL are processed
        (re-ingested content resets this flag), so unchanged resources are never
        re-extracted. Each resource is scanned in full via sliding windows
        instead of only its first chunks.
        """
        entities_extracted = 0
        mentions_created = 0
        now = datetime.now(timezone.utc)

        # Only unprocessed chunks — incremental across syncs / re-ingestions.
        # Fetch one extra to detect whether more work remains beyond the cap.
        chunks = ResourceChunk.query.filter_by(
            organization_id=self.org_id
        ).filter(
            ResourceChunk.chunk_type.in_(MENTION_CHUNK_TYPES),
            ResourceChunk.kg_processed_at.is_(None),
        ).order_by(
            ResourceChunk.resource_id, ResourceChunk.chunk_index
        ).limit(KG_CHUNKS_PER_RUN + 1).all()

        capped = len(chunks) > KG_CHUNKS_PER_RUN
        chunks = chunks[:KG_CHUNKS_PER_RUN]

        if not chunks:
            logger.info("NLP phase: no new chunks to process")
            return {'entities_extracted': 0, 'mentions_created': 0}

        # Group by resource (already ordered by resource_id, chunk_index)
        by_resource: dict[str, list[ResourceChunk]] = {}
        for chunk in chunks:
            by_resource.setdefault(str(chunk.resource_id), []).append(chunk)

        for resource_id, resource_chunks in by_resource.items():
            resource_node = self._get_node(f"resource:{resource_id}")

            # Skip LLM entity extraction for structured sources (SQL tables):
            # running it over sample rows is expensive and low-value, and the
            # live Text-to-SQL node already answers data questions. They keep
            # their structural KG (table nodes + FK edges) from phase 1.
            if resource_node and resource_node.node_type not in ('table', 'connector'):
                # Drop stale MENTIONS so re-ingested content doesn't keep
                # entities that are no longer in the document.
                KGEdge.query.filter_by(
                    org_id=self.org_id,
                    source_id=resource_node.id,
                    relation='MENTIONS',
                ).delete(synchronize_session=False)

                for window in self._chunk_windows(resource_chunks, KG_WINDOW_CHARS):
                    combined_text = '\n'.join(
                        c.content for c in window if c.content
                    )[:KG_WINDOW_CHARS]
                    if not combined_text.strip():
                        continue

                    try:
                        entities = self._extract_entities_from_text(combined_text)
                    except Exception as e:
                        logger.warning(
                            f"Entity extraction failed for resource {resource_id}: {e}"
                        )
                        continue

                    # Batch-embed all entity names from this window in ONE API
                    # call; the per-entity _upsert_node below then hits the cache
                    # instead of issuing one embeddings request per entity.
                    self._embed_many([
                        e.get('name', '').strip()
                        for e in entities if e.get('name')
                    ])

                    for entity in entities:
                        entity_type = entity.get('type', 'concept').lower()
                        entity_name = entity.get('name', '').strip()
                        if not entity_name or len(entity_name) < 2:
                            continue

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

                        edge = self._upsert_edge(
                            resource_node, entity_node, 'MENTIONS',
                            metadata={'confidence': entity.get('confidence', 1.0)}
                        )
                        if edge:
                            mentions_created += 1

            # Mark every fetched chunk processed — even when no node exists —
            # so it is never reconsidered on the next run.
            for c in resource_chunks:
                c.kg_processed_at = now

        db.session.commit()
        logger.info(
            f"NLP phase: {entities_extracted} entities, {mentions_created} mentions "
            f"from {len(chunks)} chunks"
            + (" (cap reached — re-run KG build to process the rest)" if capped else "")
        )
        return {
            'entities_extracted': entities_extracted,
            'mentions_created': mentions_created
        }

    @staticmethod
    def _chunk_windows(chunks: list, max_chars: int):
        """Yield consecutive groups of chunks whose combined length stays under
        max_chars — lets a whole document be scanned for entities, not just its
        first chunks, while keeping each LLM call bounded."""
        window: list = []
        size = 0
        for c in chunks:
            c_len = len(c.content or '')
            if window and size + c_len > max_chars:
                yield window
                window, size = [], 0
            window.append(c)
            size += c_len
        if window:
            yield window

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
                        "Return max 25 most important entities. "
                        "Return ONLY the JSON array, no other text."
                    )
                },
                {
                    "role": "user",
                    "content": f"Extract entities from:\n\n{text}"
                }
            ],
            temperature=0,
            max_tokens=1200,
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
        limit: int = 10,
        embedding: list = None,
    ) -> list[KGNode]:
        """Find nodes semantically similar to query.

        Accepts a precomputed `embedding` to avoid re-embedding the same query
        (the search agent embeds once and reuses it for vector + KG search).
        """
        query_embedding = embedding if embedding is not None else self._embed(query)

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

        if existing:
            # Only re-embed when the indexed text actually changed — avoids
            # re-embedding every node on each KG rebuild (cost + latency).
            if existing.name != name or existing.embedding is None:
                existing.embedding = self._embed(text_for_embedding or name)
            existing.name = name
            existing.kgnode_metadata = metadata
            existing.updated_at = datetime.now(timezone.utc)
            self._node_cache[external_id] = existing
            return existing

        node = KGNode(
            org_id=self.org_id,
            node_type=node_type,
            external_id=external_id,
            connector_type=connector_type,
            name=name,
            kgnode_metadata=metadata,
            embedding=self._embed(text_for_embedding or name),
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
            existing.kgedge_metadata = metadata
            return None  # already exists, not new

        edge = KGEdge(
            org_id=self.org_id,
            source_id=source.id,
            target_id=target.id,
            relation=relation,
            weight=weight,
            kgedge_metadata=metadata,
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
        """Generate (and cache) a single embedding using OpenAI."""
        if not text:
            return None
        key = text[:8000]
        cached = self._embed_cache.get(key)
        if cached is not None:
            return cached
        response = openai_client.embeddings.create(
            model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
            input=key,
            dimensions=EMBEDDING_DIMENSIONS,
        )
        emb = response.data[0].embedding
        self._embed_cache[key] = emb
        return emb

    def _embed_many(self, texts: list[str], batch_size: int = 128) -> None:
        """Embed several texts in as few API calls as possible, populating the
        cache. The OpenAI embeddings endpoint accepts a list, so N names cost
        ceil(N / batch_size) requests instead of N."""
        pending = []
        seen = set()
        for t in texts:
            if not t:
                continue
            key = t[:8000]
            if key in self._embed_cache or key in seen:
                continue
            seen.add(key)
            pending.append(key)

        for i in range(0, len(pending), batch_size):
            batch = pending[i:i + batch_size]
            response = openai_client.embeddings.create(
                model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
                input=batch,
                dimensions=EMBEDDING_DIMENSIONS,
            )
            for text_key, item in zip(batch, response.data):
                self._embed_cache[text_key] = item.embedding