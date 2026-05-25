-- init.sql
-- Script d'initialisation complet pour la base de données (version améliorée)


-- =====================================================
-- 🏢 ORGANISATION CORE
-- =====================================================
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT now(),
    deleted_at TIMESTAMP DEFAULT NULL  -- Soft delete
);

CREATE TABLE departments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT now(),
    deleted_at TIMESTAMP DEFAULT NULL  -- Soft delete
);

-- =====================================================
-- 👤 USERS & SESSIONS
-- =====================================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT,
    full_name TEXT,
    created_at TIMESTAMP DEFAULT now(),
    deleted_at TIMESTAMP DEFAULT NULL  -- Soft delete
);

-- Table de sessions pour la sécurité
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    refresh_token_hash TEXT NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    revoked_at TIMESTAMP DEFAULT NULL,
    user_agent TEXT,
    ip_address INET,
    created_at TIMESTAMP DEFAULT now()
);

-- =====================================================
-- 🎭 ROLES
-- =====================================================
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    name TEXT, -- admin, member, external
    is_system BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT now(),
    deleted_at TIMESTAMP DEFAULT NULL,  -- Soft delete
    
    -- Contrainte pour éviter les doublons par organisation
    UNIQUE(organization_id, name)
);

-- =====================================================
-- 🔗 MEMBERSHIPS (multi-tenant link)
-- =====================================================
CREATE TABLE memberships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    role_id UUID REFERENCES roles(id) ON DELETE SET NULL,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT now(),
    deleted_at TIMESTAMP DEFAULT NULL  -- Soft delete
);

-- Un user ne peut avoir qu'un seul membership actif par organisation
CREATE UNIQUE INDEX idx_memberships_unique_active 
ON memberships(user_id, organization_id) 
WHERE status = 'active' AND deleted_at IS NULL;

-- Vérifier que le rôle appartient bien à l'organisation du membership
-- (Trigger ci-dessous)

-- =====================================================
-- 🔐 PERMISSIONS (IAM-style engine) avec versioning
-- =====================================================
CREATE TABLE permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_id UUID REFERENCES roles(id) ON DELETE CASCADE,
    action TEXT,      -- read, write, execute
    resource TEXT,    -- drive, jira, chat, connector
    scope TEXT,       -- org, project, folder, etc
    allowed BOOLEAN DEFAULT true,
    valid_from TIMESTAMP DEFAULT now(),
    valid_to TIMESTAMP DEFAULT 'infinity',
    version INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT now(),
    deleted_at TIMESTAMP DEFAULT NULL  -- Soft delete
);

-- =====================================================
-- 🧠 POLICY ENGINE (advanced layer) avec versioning
-- =====================================================
CREATE TABLE policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    name TEXT,
    effect TEXT, -- allow / deny
    condition JSONB, 
    priority INT DEFAULT 0,
    valid_from TIMESTAMP DEFAULT now(),
    valid_to TIMESTAMP DEFAULT 'infinity',
    version INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT now(),
    deleted_at TIMESTAMP DEFAULT NULL  -- Soft delete
);

-- =====================================================
-- 🔌 MCP / TOOL LAYER
-- =====================================================

-- 🧩 CONNECTORS (Google Drive, Jira, etc.)
CREATE TABLE connectors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    type TEXT, -- google_drive, jira, slack, notion
    name TEXT,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT now(),
    deleted_at TIMESTAMP DEFAULT NULL  -- Soft delete
);

-- 🔑 CONNECTOR CREDENTIALS
CREATE TABLE connector_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    connector_id UUID REFERENCES connectors(id) ON DELETE CASCADE,
    encrypted_token TEXT,
    refresh_token TEXT,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    deleted_at TIMESTAMP DEFAULT NULL  -- Soft delete
);

-- 📦 TOOL SCOPES (data perimeter control)
CREATE TABLE tool_scopes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    connector_id UUID REFERENCES connectors(id) ON DELETE CASCADE,
    scope_type TEXT,  -- drive_folder, jira_project, slack_channel
    external_id TEXT, -- folderId, projectKey, channelId
    name TEXT,
    is_allowed BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT now(),
    deleted_at TIMESTAMP DEFAULT NULL,  -- Soft delete
    
    -- Unicité par connector + external_id + scope_type
    UNIQUE(connector_id, external_id, scope_type)
);

-- =====================================================
-- 📁 DATA PERIMETER LAYER
-- =====================================================

-- 📌 RESOURCES (unified abstraction of external data)
CREATE TABLE resources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    connector_id UUID REFERENCES connectors(id) ON DELETE SET NULL,
    external_id TEXT,
    type TEXT, -- file, ticket, message, doc
    title TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    deleted_at TIMESTAMP DEFAULT NULL,  -- Soft delete
    search_vector TSVECTOR,  -- Pour recherche full-text
    
    UNIQUE(connector_id, external_id)  -- Éviter les doublons
);

-- 🔗 RESOURCE BINDINGS (security layer / data firewall)
CREATE TABLE resource_bindings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resource_id UUID REFERENCES resources(id) ON DELETE CASCADE,
    tool_scope_id UUID REFERENCES tool_scopes(id) ON DELETE CASCADE,
    access_level TEXT, -- read, write
    created_at TIMESTAMP DEFAULT now(),
    deleted_at TIMESTAMP DEFAULT NULL,  -- Soft delete
    
    -- Éviter les doublons
    UNIQUE(resource_id, tool_scope_id)
);

-- =====================================================
-- 🚦 RATE LIMITING (protection MCP)
-- =====================================================
CREATE TABLE rate_limits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    connector_type TEXT, -- google_drive, jira
    max_requests INT DEFAULT 100,
    window_seconds INT DEFAULT 60,
    current_count INT DEFAULT 0,
    reset_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

-- =====================================================
-- 💬 AI LAYER
-- =====================================================

-- 🧠 CONVERSATIONS
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title TEXT,
    created_at TIMESTAMP DEFAULT now(),
    deleted_at TIMESTAMP DEFAULT NULL,  -- Soft delete
    updated_at TIMESTAMP DEFAULT now()
);

-- 💬 MESSAGES
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT, -- user, assistant, tool
    content TEXT,
    created_at TIMESTAMP DEFAULT now(),
    search_vector TSVECTOR,  -- Pour recherche full-text
    deleted_at TIMESTAMP DEFAULT NULL  -- Soft delete
);

-- 🔧 TOOL CALLS (CRITICAL for MCP tracking)
CREATE TABLE tool_calls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID REFERENCES messages(id) ON DELETE CASCADE,
    connector_id UUID REFERENCES connectors(id) ON DELETE SET NULL,
    tool_name TEXT,
    input JSONB,
    output JSONB,
    status TEXT, -- success, denied, failed
    created_at TIMESTAMP DEFAULT now(),
    deleted_at TIMESTAMP DEFAULT NULL  -- Soft delete
);

-- =====================================================
-- ✅ TOOL APPROVALS (workflow d'approbation)
-- =====================================================
CREATE TABLE tool_approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_call_id UUID REFERENCES tool_calls(id) ON DELETE CASCADE,
    approver_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    status TEXT DEFAULT 'pending', -- pending, approved, denied
    justification TEXT,
    approved_at TIMESTAMP DEFAULT NULL,
    created_at TIMESTAMP DEFAULT now()
);

-- =====================================================
-- 🔍 SECURITY & AUDIT LAYER
-- =====================================================

-- 📜 AUDIT LOGS (enterprise requirement) - Partitionné
CREATE TABLE audit_logs (
    id UUID DEFAULT gen_random_uuid(),
    organization_id UUID,
    user_id UUID,
    action TEXT,
    resource TEXT,
    tool TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT now(),

    -- created_at inclus dans la PK
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

-- Créer les partitions
CREATE TABLE audit_logs_2025 PARTITION OF audit_logs
    FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');

CREATE TABLE audit_logs_2026 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-01-01') TO ('2027-01-01');

-- Partition par défaut (sécurité)
CREATE TABLE audit_logs_default PARTITION OF audit_logs DEFAULT;


-- =====================================================
-- 📊 INDEXES pour les performances
-- =====================================================

-- Index standard

CREATE INDEX idx_users_email ON users(email) WHERE deleted_at IS NULL;
CREATE INDEX idx_departments_organization_id ON departments(organization_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_user_sessions_token ON user_sessions(refresh_token_hash);

CREATE INDEX idx_memberships_user_id ON memberships(user_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_memberships_organization_id ON memberships(organization_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_memberships_role_id ON memberships(role_id) WHERE deleted_at IS NULL;

CREATE INDEX idx_permissions_role_id ON permissions(role_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_permissions_valid ON permissions(role_id, valid_from, valid_to) WHERE deleted_at IS NULL;

CREATE INDEX idx_policies_organization_id ON policies(organization_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_policies_priority ON policies(priority, valid_from, valid_to) WHERE deleted_at IS NULL;

CREATE INDEX idx_connectors_organization_id ON connectors(organization_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_connectors_status ON connectors(status) WHERE deleted_at IS NULL;

CREATE INDEX idx_connector_credentials_connector_id ON connector_credentials(connector_id) WHERE deleted_at IS NULL;

CREATE INDEX idx_tool_scopes_connector_id ON tool_scopes(connector_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_tool_scopes_scope_type ON tool_scopes(scope_type) WHERE deleted_at IS NULL;

CREATE INDEX idx_resources_organization_id ON resources(organization_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_resources_connector_id ON resources(connector_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_resources_type ON resources(type) WHERE deleted_at IS NULL;

-- Index full-text search
CREATE INDEX idx_resources_search ON resources USING GIN(search_vector);
CREATE INDEX idx_messages_search ON messages USING GIN(search_vector);

CREATE INDEX idx_resource_bindings_resource_id ON resource_bindings(resource_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_resource_bindings_tool_scope_id ON resource_bindings(tool_scope_id) WHERE deleted_at IS NULL;

CREATE INDEX idx_rate_limits_organization_id ON rate_limits(organization_id);
CREATE INDEX idx_rate_limits_reset ON rate_limits(reset_at);

CREATE INDEX idx_conversations_organization_id ON conversations(organization_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_conversations_user_id ON conversations(user_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_conversations_created_at ON conversations(created_at);

CREATE INDEX idx_messages_conversation_id ON messages(conversation_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_messages_created_at ON messages(created_at);

CREATE INDEX idx_tool_calls_message_id ON tool_calls(message_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_tool_calls_connector_id ON tool_calls(connector_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_tool_calls_status ON tool_calls(status) WHERE deleted_at IS NULL;

CREATE INDEX idx_tool_approvals_tool_call_id ON tool_approvals(tool_call_id);
CREATE INDEX idx_tool_approvals_status ON tool_approvals(status);

CREATE INDEX idx_audit_logs_organization_id ON audit_logs(organization_id);
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);

-- Index composite pour les recherches fréquentes
CREATE INDEX idx_tool_scopes_connector_scope ON tool_scopes(connector_id, scope_type) WHERE deleted_at IS NULL;
CREATE INDEX idx_permissions_role_resource ON permissions(role_id, resource) WHERE deleted_at IS NULL;

-- =====================================================
-- 🔧 TRIGGER pour vérifier la cohérence role/organization
-- =====================================================

CREATE OR REPLACE FUNCTION check_membership_role_organization()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.role_id IS NOT NULL THEN
        IF NOT EXISTS (
            SELECT 1 FROM roles 
            WHERE id = NEW.role_id 
            AND organization_id = NEW.organization_id
            AND deleted_at IS NULL
        ) THEN
            RAISE EXCEPTION 'Role % does not belong to organization %', NEW.role_id, NEW.organization_id;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_check_membership_role
BEFORE INSERT OR UPDATE ON memberships
FOR EACH ROW
EXECUTE FUNCTION check_membership_role_organization();

-- =====================================================
-- 🔧 TRIGGER pour maintenir les vecteurs de recherche
-- =====================================================

CREATE OR REPLACE FUNCTION update_resource_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector := setweight(to_tsvector('french', COALESCE(NEW.title, '')), 'A') ||
                         setweight(to_tsvector('french', COALESCE(NEW.metadata::text, '')), 'B');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_resource_search
BEFORE INSERT OR UPDATE ON resources
FOR EACH ROW
EXECUTE FUNCTION update_resource_search_vector();

CREATE OR REPLACE FUNCTION update_message_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector := to_tsvector('french', COALESCE(NEW.content, ''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_message_search
BEFORE INSERT OR UPDATE ON messages
FOR EACH ROW
EXECUTE FUNCTION update_message_search_vector();