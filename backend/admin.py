"""
Flask-Admin configuration for FlexiAnalyse
==========================================
Compatible avec Flask-Admin 2.2.0
"""

from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from models.knowledge_graph import KGNode, KGEdge
from models.resource import Resource, ResourceChunk
from models.connector import Connector, ConnectorSync
from config.extensions import db

# ============================================================================
# DASHBOARD PERSONNALISÉ
# ============================================================================

class DashboardView(AdminIndexView):
    """Dashboard avec statistiques"""
    
    @expose('/')
    def index(self):
        stats = {
            'total_nodes': KGNode.query.count(),
            'total_edges': KGEdge.query.count(),
            'total_resources': Resource.query.count(),
            'total_connectors': Connector.query.count(),
            'total_syncs': ConnectorSync.query.count(),
        }
        
        # Statistiques par type de nœud
        node_types = db.session.query(
            KGNode.node_type, db.func.count(KGNode.id)
        ).group_by(KGNode.node_type).all()
        
        stats['node_types'] = dict(node_types)
        
        return self.render('admin/index.html', stats=stats)

# ============================================================================
# INSTANCE ADMIN - CORRIGÉE POUR FLASK-ADMIN 2.2.0
# ============================================================================

# ⚠️ Dans Flask-Admin 2.2.0, on utilise 'url' au lieu de 'base_url'
# et 'template_mode' n'existe plus
admin = Admin(
    name='FlexiAnalyse Admin',
    url='/admin',  # ← CHANGÉ : url au lieu de base_url
    index_view=DashboardView()
)

# ============================================================================
# VUES PERSONNALISÉES
# ============================================================================

class KGNodeView(ModelView):
    """Nœuds du Knowledge Graph"""
    
    column_list = ('name', 'node_type', 'connector_type', 'org_id', 'created_at')
    column_filters = ('node_type', 'connector_type', 'org_id', 'created_at')
    column_searchable_list = ('name', 'external_id', 'org_id')
    column_default_sort = ('created_at', True)
    page_size = 50
    
    column_labels = {
        'name': 'Nom',
        'node_type': 'Type de nœud',
        'connector_type': 'Type de connecteur',
        'org_id': 'Organisation',
        'external_id': 'ID Externe',
        'created_at': 'Créé le'
    }
    
    column_formatters = {
        'created_at': lambda v, c, m, p: m.created_at.strftime('%Y-%m-%d %H:%M:%S') if m.created_at else ''
    }


class KGEdgeView(ModelView):
    """Relations du Knowledge Graph"""
    
    column_list = ('source_id', 'target_id', 'relation', 'weight', 'created_at')
    column_filters = ('relation', 'weight')
    column_searchable_list = ('source_id', 'target_id', 'relation')
    column_default_sort = ('created_at', True)
    page_size = 50
    
    column_labels = {
        'source_id': 'Source',
        'target_id': 'Cible',
        'relation': 'Type de relation',
        'weight': 'Poids'
    }
    
    column_formatters = {
        'source_id': lambda v, c, m, p: KGNode.query.get(m.source_id).name if KGNode.query.get(m.source_id) else str(m.source_id),
        'target_id': lambda v, c, m, p: KGNode.query.get(m.target_id).name if KGNode.query.get(m.target_id) else str(m.target_id),
        'created_at': lambda v, c, m, p: m.created_at.strftime('%Y-%m-%d %H:%M:%S') if m.created_at else '',
    }


class ResourceView(ModelView):
    """Ressources ingérées"""
    
    column_list = ('title', 'type', 'ingestion_status', 'connector_id', 'file_size_bytes', 'ingested_at')
    column_filters = ('type', 'ingestion_status', 'connector_id')
    column_searchable_list = ('title', 'external_id')
    column_default_sort = ('ingested_at', True)
    page_size = 50
    
    column_labels = {
        'title': 'Titre',
        'type': 'Type',
        'ingestion_status': 'Statut',
        'connector_id': 'Connecteur',
        'file_size_bytes': 'Taille (bytes)',
        'ingested_at': 'Ingéré le'
    }
    
    column_formatters = {
        'ingested_at': lambda v, c, m, p: m.ingested_at.strftime('%Y-%m-%d %H:%M:%S') if m.ingested_at else '',
        'file_size_bytes': lambda v, c, m, p: f"{m.file_size_bytes:,}" if m.file_size_bytes else ''
    }
    
    form_excluded_columns = ('chunks', 'created_at', 'updated_at')


class ResourceChunkView(ModelView):
    """Chunks de ressources"""
    
    column_list = ('chunk_index', 'chunk_type', 'content', 'resource_id', 'token_count')
    column_filters = ('chunk_type',)
    column_searchable_list = ('content',)
    page_size = 50
    
    column_labels = {
        'chunk_index': 'Index',
        'chunk_type': 'Type',
        'content': 'Contenu',
        'resource_id': 'Ressource',
        'token_count': 'Tokens'
    }
    
    column_formatters = {
        'content': lambda v, c, m, p: (m.content[:200] + '...') if m.content and len(m.content) > 200 else m.content
    }


class ConnectorView(ModelView):
    """Connecteurs"""
    
    column_list = ('name', 'type', 'status', 'created_at')
    column_filters = ('type', 'status')
    column_searchable_list = ('name',)
    column_default_sort = ('created_at', True)
    page_size = 50
    
    column_labels = {
        'name': 'Nom',
        'type': 'Type',
        'status': 'Statut',
        'created_at': 'Créé le'
    }
    
    column_formatters = {
        'created_at': lambda v, c, m, p: m.created_at.strftime('%Y-%m-%d %H:%M:%S') if m.created_at else ''
    }
    
    form_excluded_columns = ('credentials', 'encrypted_config')


class ConnectorSyncView(ModelView):
    """Historique des synchronisations"""
    
    column_list = ('connector_id', 'status', 'resources_processed', 'resources_created', 'batches_completed', 'total_batches', 'completed_at')
    column_filters = ('status',)
    column_searchable_list = ('connector_id',)
    column_default_sort = ('completed_at', True)
    page_size = 50
    
    column_labels = {
        'connector_id': 'Connecteur',
        'status': 'Statut',
        'resources_processed': 'Traitées',
        'resources_created': 'Créées',
        'batches_completed': 'Batches OK',
        'total_batches': 'Total Batches',
        'completed_at': 'Terminé le'
    }
    
    column_formatters = {
        'completed_at': lambda v, c, m, p: m.completed_at.strftime('%Y-%m-%d %H:%M:%S') if m.completed_at else ''
    }


# ============================================================================
# INITIALISATION
# ============================================================================

def init_admin(app):
    """Initialiser Flask-Admin avec l'application Flask"""
    
    admin.init_app(app)
    
    # Ajouter les vues avec catégories
    admin.add_view(KGNodeView(KGNode, db.session, name='KG Nodes', category='Knowledge Graph'))
    admin.add_view(KGEdgeView(KGEdge, db.session, name='KG Edges', category='Knowledge Graph'))
    admin.add_view(ResourceView(Resource, db.session, name='Resources', category='Ingestion'))
    admin.add_view(ResourceChunkView(ResourceChunk, db.session, name='Chunks', category='Ingestion'))
    admin.add_view(ConnectorView(Connector, db.session, name='Connectors', category='Connectors'))
    admin.add_view(ConnectorSyncView(ConnectorSync, db.session, name='Sync History', category='Connectors'))
    
    return admin