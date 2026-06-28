 # ai/agents/office_manager/sub_agents/search_agent.py
"""
Enterprise Search Agent avec LangGraph
======================================
Raisonnement en plusieurs étapes :
1. Analyse de la requête
2. Décomposition en sous-requêtes
3. Recherche vectorielle + KG
4. Reranking
5. Synthèse avec citations
"""

import os
import json
import time
from typing import Dict, Any, List
from datetime import datetime

from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser

from config.extensions import db
from models.resource import Resource, ResourceChunk
from models.knowledge_graph import KGNode, KGEdge
from ai.agents.office_manager.state import OfficeManagerState

# ============================================================================
# PROMPTS SPÉCIALISÉS
# ============================================================================

QUERY_ANALYSIS_PROMPT = """You are an expert search query analyzer for an enterprise system.

Analyze the user's search query and:
1. Identify the main search intent
2. Decompose into 1-3 sub-queries if needed
3. Identify relevant data sources (google_drive, dropbox, sql, all)
4. Determine if knowledge graph should be consulted
5. Identify any filters (date, file type, department, etc.)

User Query: {query}
Organization Context: {context}

Return JSON:
{{
    "main_intent": "string",
    "sub_queries": ["query1", "query2"],
    "sources": ["google_drive", "sql"],
    "use_knowledge_graph": true/false,
    "filters": {{"date_range": null, "file_type": null}},
    "complexity": "simple|medium|complex"
}}"""

RERANK_PROMPT = """Rerank these search results by relevance to the query.
Return the indices of the top results, ordered by relevance.

Query: {query}
Results: {results}

Return ONLY a JSON array of integers: [0, 2, 5, ...]"""

# Remplace TON SYNTHESIS_PROMPT par celui-ci (plus directif) :
SYNTHESIS_PROMPT = """You are a search assistant. Answer the user's query using the provided context.

The context contains REAL document content from the company's files.

QUERY: {query}

CONTEXT:
{context}

INSTRUCTIONS:
- Answer in the SAME LANGUAGE as the query
- If the query asks about a person, extract ALL information about that person from the context
- Include: name, email, phone, skills, experience, education, location - whatever is present
- Cite sources using [1], [2], etc.
- DO NOT say "the sources don't contain information" if you see the person's name in the context
- BE DIRECT and SPECIFIC

YOUR ANSWER:"""


# ============================================================================
# AGENT LANGGRAPH
# ============================================================================

class SearchAgent:
    """Agent de recherche avec LangGraph"""
    
    def __init__(self, org_id: str):
        self.org_id = org_id
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.1
        )
        self.embeddings = OpenAIEmbeddings(
            model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        )
        
        # Construire le graphe
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Construit le graphe de raisonnement pour la recherche"""
        
        workflow = StateGraph(OfficeManagerState)
        
        # Ajouter les nœuds
        workflow.add_node("analyze_query", self.analyze_query)
        workflow.add_node("decompose_query", self.decompose_query)
        workflow.add_node("vector_search", self.vector_search)
        workflow.add_node("kg_search", self.knowledge_graph_search)
        workflow.add_node("rerank_results", self.rerank_results)
        workflow.add_node("synthesize", self.synthesize_answer)
        workflow.add_node("handle_error", self.handle_error)
        
        # Définir le flux
        workflow.set_entry_point("analyze_query")
        
        # Après analyse, décider si on décompose ou pas
        workflow.add_conditional_edges(
            "analyze_query",
            self.should_decompose,
            {
                "decompose": "decompose_query",
                "search": "vector_search",
                "error": "handle_error"
            }
        )
        
        # Après décomposition, aller à la recherche
        workflow.add_edge("decompose_query", "vector_search")
        
        # Après recherche vectorielle, décider si on utilise le KG
        workflow.add_conditional_edges(
            "vector_search",
            self.should_use_kg,
            {
                "kg": "kg_search",
                "rerank": "rerank_results",
                "error": "handle_error"
            }
        )
        
        # Après KG, rerank
        workflow.add_edge("kg_search", "rerank_results")
        
        # Après rerank, synthétiser
        workflow.add_edge("rerank_results", "synthesize")
        
        # Fin
        workflow.add_edge("synthesize", END)
        workflow.add_edge("handle_error", END)
        
        return workflow.compile()
    
    # ========================================================================
    # NŒUDS DU GRAPHE
    # ========================================================================
    
    def analyze_query(self, state: OfficeManagerState) -> OfficeManagerState:
        """Analyse l'intention de la requête"""
        start_time = time.time()
        
        try:
            # Analyser la requête avec LLM
            prompt = ChatPromptTemplate.from_template(QUERY_ANALYSIS_PROMPT)
            chain = prompt | self.llm | JsonOutputParser()
            
            analysis = chain.invoke({
                "query": state['user_message'],
                "context": json.dumps(state.get('context', {}))
            })
            
            state['intent'] = analysis['main_intent']
            state['intent_confidence'] = 0.9
            state['context']['search_analysis'] = analysis
            
            # Déterminer si la requête est complexe
            if analysis['complexity'] == 'complex' or len(analysis['sub_queries']) > 1:
                state['next_step'] = 'decompose_query'
            else:
                state['next_step'] = 'vector_search'
            
            state['messages'].append(
                AIMessage(content=f"Query analyzed: {analysis['main_intent']}")
            )
            
        except Exception as e:
            state['error'] = f"Query analysis failed: {str(e)}"
            state['next_step'] = 'error'
        
        # Enregistrer le résultat
        state['sub_agent_results'].append({
            'agent_name': 'search_agent',
            'status': 'success' if not state.get('error') else 'failed',
            'result': state.get('context', {}).get('search_analysis', {}),
            'error': state.get('error'),
            'execution_time': time.time() - start_time
        })
        
        return state
    
    def decompose_query(self, state: OfficeManagerState) -> OfficeManagerState:
        """Décompose la requête en sous-requêtes"""
        
        analysis = state['context'].get('search_analysis', {})
        state['context']['active_sub_queries'] = analysis.get('sub_queries', [state['user_message']])
        state['context']['search_results'] = []
        
        state['messages'].append(
            AIMessage(content=f"Decomposed into {len(analysis.get('sub_queries', []))} sub-queries")
        )
        
        state['next_step'] = 'vector_search'
        return state
    
    _STOPWORDS = {
        'who', 'what', 'where', 'when', 'why', 'how', 'is', 'are', 'the', 'a', 'an',
        'of', 'to', 'in', 'on', 'for', 'and', 'or', 'me', 'my', 'tell', 'about',
        'give', 'show', 'find', 'get', 'can', 'you', 'please', 'do', 'does',
        'qui', 'est', 'que', 'quoi', 'quel', 'quelle', 'le', 'la', 'les', 'de',
        'des', 'du', 'un', 'une', 'sur', 'pour', 'dans', 'avec', 'moi', 'mon',
    }

    def _keywords(self, text_value: str) -> list[str]:
        """Extract significant keywords from a query for hybrid keyword matching."""
        import re
        words = re.findall(r'\w+', (text_value or '').lower())
        seen = []
        for w in words:
            if len(w) > 2 and w not in self._STOPWORDS and w not in seen:
                seen.append(w)
        return seen[:6]

    def vector_search(self, state: OfficeManagerState) -> OfficeManagerState:
        """
        Recherche hybride (sémantique + mots-clés) dans pgvector.
        ⚠️ AUCUN FILTRE par type de connecteur.
        """
        
        try:
            sub_queries = state['context'].get('active_sub_queries', [state['user_message']])
            
            # Extraire les mots-clés pour le boost
            keywords = self._keywords(state['user_message'])
            print(f"🔑 Keywords: {keywords}")
            
            kw_params = {}
            boost_terms = []
            
            for i, kw in enumerate(keywords):
                kw_params[f'kw{i}'] = f'%{kw}%'
                # Boost titre (nom de fichier) = très fort signal
                boost_terms.append(f"COALESCE(CASE WHEN r.title ILIKE :kw{i} THEN 0.6 ELSE 0 END, 0)")
                # Boost contenu
                boost_terms.append(f"COALESCE(CASE WHEN rc.content ILIKE :kw{i} THEN 0.4 ELSE 0 END, 0)")
            
            keyword_score_sql = " + ".join(boost_terms) if boost_terms else "0.0"
            
            all_results = []
            
            for query in sub_queries:
                query_embedding = self.embeddings.embed_query(query)
                
                from sqlalchemy import text
                
                # ⚠️ AUCUN FILTRE c.type - on cherche dans TOUS les connecteurs
                # ⚠️ CAST explicite en FLOAT pour éviter Decimal + float
                sql = f"""
                    SELECT 
                        rc.id,
                        rc.content,
                        rc.chunk_type,
                        rc.chunk_metadata,
                        r.title as resource_title,
                        r.type as resource_type,
                        r.external_id as resource_external_id,
                        c.name as connector_name,
                        c.type as connector_type,
                        CAST(1 - (rc.embedding <=> CAST(:embedding AS vector)) AS FLOAT) as similarity,
                        CAST(({keyword_score_sql}) AS FLOAT) as keyword_score
                    FROM resource_chunks rc
                    JOIN resources r ON rc.resource_id = r.id
                    JOIN connectors c ON r.connector_id = c.id
                    WHERE rc.organization_id = :org_id
                    AND rc.embedding IS NOT NULL
                    ORDER BY CAST(1 - (rc.embedding <=> CAST(:embedding AS vector)) AS FLOAT) + CAST(({keyword_score_sql}) AS FLOAT) DESC
                    LIMIT 25
                """
                
                params = {
                    'embedding': str(query_embedding),
                    'org_id': self.org_id,
                    **kw_params,
                }
                
                results = db.session.execute(text(sql), params).fetchall()
                
                for r in results:
                    # ⚠️ Conversion explicite en float pour éviter Decimal
                    similarity = float(r[9]) if r[9] is not None else 0.0
                    keyword_score = float(r[10]) if r[10] is not None else 0.0
                    
                    all_results.append({
                        'chunk_id': str(r[0]),
                        'content': r[1] or '',
                        'chunk_type': r[2],
                        'metadata': r[3],
                        'resource_title': r[4] or '',
                        'resource_type': r[5],
                        'connector_name': r[7] or '',
                        'connector_type': r[8],
                        'similarity': round(similarity, 4),
                        'keyword_score': round(keyword_score, 4),
                        'score': round(similarity + keyword_score, 4),
                        'sub_query': query
                    })
            
            # Dédupliquer et trier par score hybride
            seen = set()
            unique_results = []
            for r in sorted(all_results, key=lambda x: x['score'], reverse=True):
                if r['chunk_id'] not in seen:
                    seen.add(r['chunk_id'])
                    unique_results.append(r)
            
            state['context']['vector_results'] = unique_results[:20]
            
            # LOG TOP 5
            print(f"\n🔍 TOP 5 RÉSULTATS:")
            for i, r in enumerate(unique_results[:5]):
                print(f"  [{i+1}] {r['connector_name']} → {r['resource_title']}")
                print(f"       Score: {r['score']:.4f} (sim: {r['similarity']:.4f}, boost: {r['keyword_score']:.4f})")
                content_preview = (r['content'] or '')[:100].replace('\n', ' ')
                print(f"       Content: {content_preview}...")
            
            state['messages'].append(
                AIMessage(content=f"Found {len(unique_results)} relevant documents")
            )
            
            state['next_step'] = 'rerank'
            
        except Exception as e:
            print(f"❌ Vector search error: {e}")
            import traceback
            traceback.print_exc()
            state['error'] = f"Vector search failed: {str(e)}"
            state['next_step'] = 'error'
            return state
        
        return state
    
    def knowledge_graph_search(self, state: OfficeManagerState) -> OfficeManagerState:
        """Recherche dans le Knowledge Graph"""
        
        try:
            query = state['user_message']
            query_embedding = self.embeddings.embed_query(query)
            
            # Rechercher les nœuds pertinents
            nodes = KGNode.query.filter_by(
                org_id=self.org_id
            ).filter(
                KGNode.embedding.isnot(None)
            ).order_by(
                KGNode.embedding.cosine_distance(query_embedding)
            ).limit(10).all()
            
            kg_results = []
            for node in nodes:
                # Récupérer les relations
                edges = KGEdge.query.filter_by(
                    org_id=self.org_id
                ).filter(
                    (KGEdge.source_id == node.id) | (KGEdge.target_id == node.id)
                ).limit(20).all()
                
                kg_results.append({
                    'node_name': node.name,
                    'node_type': node.node_type,
                    'metadata': node.metadata,
                    'relations': [{
                        'source': KGNode.query.get(e.source_id).name if e.source_id != node.id else node.name,
                        'target': KGNode.query.get(e.target_id).name if e.target_id != node.id else node.name,
                        'relation': e.relation,
                        'weight': e.weight
                    } for e in edges]
                })
            
            state['context']['kg_results'] = kg_results
            
            state['messages'].append(
                AIMessage(content=f"KG: Found {len(kg_results)} relevant entities")
            )
            
            state['next_step'] = 'rerank_results'
            
        except Exception as e:
            # KG failure is non-critical
            state['context']['kg_results'] = []
            state['next_step'] = 'rerank_results'
        
        return state
    
    def _to_candidate(self, r: Dict[str, Any]) -> Dict[str, Any]:
        """Normalise un résultat vectoriel en candidat de réponse."""
        
        # Construire une source lisible
        connector_name = r.get('connector_name', '')
        resource_title = r.get('resource_title', '')
        
        if connector_name and resource_title:
            source = f"{connector_name} → {resource_title}"
        elif resource_title:
            source = resource_title
        else:
            source = connector_name or 'Unknown'
        
        return {
            'type': 'document',
            'content': r.get('content', ''),
            'source': source,
            'resource_title': resource_title,
            'connector_name': connector_name,
            'connector_type': r.get('connector_type', ''),
            'similarity': r.get('score', r.get('similarity', 0)),
            'full_data': r,
        }

    def rerank_results(self, state: OfficeManagerState) -> OfficeManagerState:
        """Rerank document results (connector files) by relevance."""
        
        try:
            vector_results = state['context'].get('vector_results', [])
            
            if not vector_results:
                state['context']['ranked_results'] = []
                state['next_step'] = 'synthesize'
                return state
            
            # Candidats = uniquement les fichiers des connecteurs (pas le KG)
            candidates = [self._to_candidate(r) for r in vector_results[:20]]
            
            # Peu de candidats -> garder l'ordre de similarité
            if len(candidates) <= 8:
                state['context']['ranked_results'] = candidates
                state['next_step'] = 'synthesize'
                return state
            
            # Rerank avec LLM
            candidates_text = "\n".join([
                f"[{i}] Score: {c['similarity']:.2f} | {c['source']}\n{c['content'][:250]}"
                for i, c in enumerate(candidates)
            ])
            
            prompt = ChatPromptTemplate.from_template(RERANK_PROMPT)
            chain = prompt | self.llm | StrOutputParser()
            
            response = chain.invoke({
                "query": state['user_message'],
                "results": candidates_text
            })
            
            try:
                response = response.strip()
                if response.startswith('```'):
                    response = response.split('```')[1]
                    if response.startswith('json'):
                        response = response[4:]
                ranked_indices = json.loads(response)
                ranked_results = [candidates[i] for i in ranked_indices if 0 <= i < len(candidates)]
                if not ranked_results:
                    ranked_results = sorted(candidates, key=lambda x: x['similarity'], reverse=True)
            except Exception:
                ranked_results = sorted(candidates, key=lambda x: x['similarity'], reverse=True)
            
            state['context']['ranked_results'] = ranked_results[:10]
            state['messages'].append(
                AIMessage(content=f"Reranked to top {len(ranked_results[:10])} documents")
            )
            
        except Exception:
            state['context']['ranked_results'] = [
                self._to_candidate(r) for r in state['context'].get('vector_results', [])[:10]
            ]
        
        state['next_step'] = 'synthesize'
        return state
    
    def synthesize_answer(self, state: OfficeManagerState) -> OfficeManagerState:
        """Synthétise la réponse finale"""
        
        try:
            ranked_results = state['context'].get('ranked_results', [])
            
            if not ranked_results:
                state['final_response'] = "No relevant information found in your connected files."
                state['citations'] = []
                state['search_results'] = {'answer': state['final_response'], 'citations': [], 'total_sources': 0}
                return state
            
            # Préparer le contexte (contenu réel des fichiers)
            query = state['user_message'].lower()
            relevant_results = []
            
            for r in ranked_results:
                content = r.get('content', '').lower()
                title = r.get('resource_title', '').lower()
                
                # Vérifier si le contenu ou le titre contient des mots de la requête
                query_words = [w for w in query.split() if len(w) > 2]
                is_relevant = any(
                    word in content or word in title
                    for word in query_words
                )
                
                if is_relevant or len(ranked_results) <= 3:
                    relevant_results.append(r)
            
            if not relevant_results:
                relevant_results = ranked_results[:3]
            
            context_parts = []
            citations = []

            for i, r in enumerate(relevant_results[:8]):  # Prendre plus de résultats
                source = r.get('source', 'Unknown')
                content = r.get('content', '')
                
                # Ne pas tronquer le contenu - donner le maximum au LLM
                context_parts.append(f"[{i+1}] SOURCE: {source}\nCONTENT: {content}")
                
                citations.append({
                    'index': i + 1,
                    'source': source,
                    'type': r.get('type', 'document'),
                    'similarity': r.get('similarity', 0)
                })

            context = "\n\n---\n\n".join(context_parts)
            
            print(f"📊 Contexte total: {len(context)} caractères")
        
            # Synthétiser avec LLM
            prompt = ChatPromptTemplate.from_template(SYNTHESIS_PROMPT)
            chain = prompt | self.llm | StrOutputParser()
            
            answer = chain.invoke({
                "query": state['user_message'],
                "context": context
            })
            
            print(f"✅ Réponse générée: {answer[:200]}...")
            
            state['final_response'] = answer
            state['citations'] = citations
            
            state['messages'].append(
                AIMessage(content=answer)
            )
            
        except Exception as e:
            print(f"❌ Erreur synthèse: {e}")
            state['final_response'] = f"Erreur lors de la synthèse: {str(e)}"
            state['citations'] = []
        
        state['search_results'] = {
            'answer': state['final_response'],
            'citations': state['citations'],
            'total_sources': len(ranked_results)
        }
        
        return state
    
    def handle_error(self, state: OfficeManagerState) -> OfficeManagerState:
        """Gère les erreurs"""
        state['final_response'] = f"Search failed: {state.get('error', 'Unknown error')}"
        state['next_step'] = 'done'
        return state
    
    # ========================================================================
    # FONCTIONS DE ROUTAGE
    # ========================================================================
    
    def should_decompose(self, state: OfficeManagerState) -> str:
        """Décide si on doit décomposer la requête"""
        if state.get('error'):
            return 'error'
        if state.get('next_step') == 'decompose_query':
            return 'decompose'
        return 'search'
    
    def should_use_kg(self, state: OfficeManagerState) -> str:
        """Resource search relies on connector files, not the knowledge graph."""
        if state.get('error'):
            return 'error'
        return 'rerank'

    def _should_use_kg_legacy(self, state: OfficeManagerState) -> str:
        """(unused) ancien routage KG"""
        if state.get('error'):
            return 'error'
        if state['context'].get('search_analysis', {}).get('use_knowledge_graph', False):
            return 'kg'
        return 'rerank'
    
    # ========================================================================
    # INTERFACE PUBLIQUE
    # ========================================================================
    
    def search(self, query: str, context: Dict = None) -> Dict[str, Any]:
        """Interface principale de recherche"""
        
        initial_state = {
            'user_message': query,
            'org_id': self.org_id,
            'messages': [HumanMessage(content=query)],
            'context': context or {},
            'sub_agent_results': [],
            'citations': [],
            'next_step': 'analyze_query',
            'should_continue': True,
            'metadata': {}
        }
        
        # Exécuter le graphe
        final_state = self.graph.invoke(initial_state)
        
        return {
            'answer': final_state.get('final_response', ''),
            'citations': final_state.get('citations', []),
            'search_results': final_state.get('search_results', {}),
            'messages': final_state.get('messages', []),
            'execution_trace': final_state.get('sub_agent_results', [])
        }