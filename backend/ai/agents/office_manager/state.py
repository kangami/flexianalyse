# ai/agents/office_manager/state.py
"""
État partagé entre tous les agents LangGraph
============================================
Utilise TypedDict pour la validation des données
"""

from typing import TypedDict, List, Dict, Any, Optional, Annotated
from typing_extensions import NotRequired
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
import operator


class SubAgentResult(TypedDict):
    """Résultat d'un sous-agent"""
    agent_name: str
    status: str  # 'success', 'failed', 'pending'
    result: Dict[str, Any]
    error: Optional[str]
    execution_time: float


class OfficeManagerState(TypedDict):
    """
    État global de l'Office Manager Agent.
    Partagé entre tous les sous-agents via LangGraph.
    """
    # Input
    user_message: str
    org_id: str
    user_id: Optional[str]
    conversation_id: Optional[str]
    
    # Messages (historique de conversation)
    messages: Annotated[List[BaseMessage], add_messages]
    
    # Analyse de l'intention
    intent: Optional[str]
    intent_confidence: Optional[float]
    required_agents: List[str]
    
    # Contexte
    context: Dict[str, Any]
    search_results: Optional[Dict[str, Any]]
    knowledge_graph_context: Optional[Dict[str, Any]]
    
    # Résultats des sous-agents
    sub_agent_results: Annotated[List[SubAgentResult], operator.add]
    
    # Réponse finale
    final_response: Optional[str]
    citations: List[Dict[str, Any]]
    
    # Contrôle de flux
    next_step: str  # 'intent_analysis', 'search', 'report', 'followup', 'meeting', 'respond'
    should_continue: bool
    error: Optional[str]
    
    # Metadata
    metadata: Dict[str, Any]