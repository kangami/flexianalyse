"""ServiceLocator — injecte les repositories. Aucune logique métier ici."""
from repositories import (
    OrganizationRepository,
    DepartmentRepository,
    UserRepository,
    UserSessionRepository,
    RoleRepository,
    MembershipRepository,
    PermissionRepository,
    PolicyRepository,
    RolePermissionRepository,
    ConnectorRepository,
    ConnectorCredentialsRepository,
    ToolScopeRepository,
    ResourceRepository,
    ResourceBindingRepository,
    RateLimitRepository,
    ConversationRepository,
    MessageRepository,
    ToolCallRepository,
    ToolApprovalRepository,
    AuditLogRepository,
)


class ServiceLocator:
    """Localisateur de services — injecte les repositories."""

    def __init__(self, db_connection=None):
        self._db = db_connection
        self._repos = {}

    @property
    def db(self):
        if self._db is None:
            raise RuntimeError("DB connection not initialized. Call init_db() first.")
        return self._db

    def init_db(self, db_connection):
        self._db = db_connection
        self._repos.clear()

    @property
    def organizations(self) -> OrganizationRepository:
        if "organizations" not in self._repos:
            self._repos["organizations"] = OrganizationRepository(self.db)
        return self._repos["organizations"]

    @property
    def departments(self) -> DepartmentRepository:
        if "departments" not in self._repos:
            self._repos["departments"] = DepartmentRepository(self.db)
        return self._repos["departments"]

    @property
    def users(self) -> UserRepository:
        if "users" not in self._repos:
            self._repos["users"] = UserRepository(self.db)
        return self._repos["users"]

    @property
    def user_sessions(self) -> UserSessionRepository:
        if "user_sessions" not in self._repos:
            self._repos["user_sessions"] = UserSessionRepository(self.db)
        return self._repos["user_sessions"]

    @property
    def roles(self) -> RoleRepository:
        if "roles" not in self._repos:
            self._repos["roles"] = RoleRepository(self.db)
        return self._repos["roles"]

    @property
    def memberships(self) -> MembershipRepository:
        if "memberships" not in self._repos:
            self._repos["memberships"] = MembershipRepository(self.db)
        return self._repos["memberships"]

    @property
    def permissions(self) -> PermissionRepository:
        if "permissions" not in self._repos:
            self._repos["permissions"] = PermissionRepository(self.db)
        return self._repos["permissions"]

    @property
    def role_permissions(self) -> RolePermissionRepository:
        if "role_permissions" not in self._repos:
            self._repos["role_permissions"] = RolePermissionRepository(self.db)
        return self._repos["role_permissions"]

    @property
    def policies(self) -> PolicyRepository:
        if "policies" not in self._repos:
            self._repos["policies"] = PolicyRepository(self.db)
        return self._repos["policies"]

    @property
    def connectors(self) -> ConnectorRepository:
        if "connectors" not in self._repos:
            self._repos["connectors"] = ConnectorRepository(self.db)
        return self._repos["connectors"]

    @property
    def connector_credentials(self) -> ConnectorCredentialsRepository:
        if "connector_credentials" not in self._repos:
            self._repos["connector_credentials"] = ConnectorCredentialsRepository(self.db)
        return self._repos["connector_credentials"]

    @property
    def tool_scopes(self) -> ToolScopeRepository:
        if "tool_scopes" not in self._repos:
            self._repos["tool_scopes"] = ToolScopeRepository(self.db)
        return self._repos["tool_scopes"]

    @property
    def resources(self) -> ResourceRepository:
        if "resources" not in self._repos:
            self._repos["resources"] = ResourceRepository(self.db)
        return self._repos["resources"]

    @property
    def resource_bindings(self) -> ResourceBindingRepository:
        if "resource_bindings" not in self._repos:
            self._repos["resource_bindings"] = ResourceBindingRepository(self.db)
        return self._repos["resource_bindings"]

    @property
    def rate_limits(self) -> RateLimitRepository:
        if "rate_limits" not in self._repos:
            self._repos["rate_limits"] = RateLimitRepository(self.db)
        return self._repos["rate_limits"]

    @property
    def conversations(self) -> ConversationRepository:
        if "conversations" not in self._repos:
            self._repos["conversations"] = ConversationRepository(self.db)
        return self._repos["conversations"]

    @property
    def messages(self) -> MessageRepository:
        if "messages" not in self._repos:
            self._repos["messages"] = MessageRepository(self.db)
        return self._repos["messages"]

    @property
    def tool_calls(self) -> ToolCallRepository:
        if "tool_calls" not in self._repos:
            self._repos["tool_calls"] = ToolCallRepository(self.db)
        return self._repos["tool_calls"]

    @property
    def tool_approvals(self) -> ToolApprovalRepository:
        if "tool_approvals" not in self._repos:
            self._repos["tool_approvals"] = ToolApprovalRepository(self.db)
        return self._repos["tool_approvals"]

    @property
    def audit_logs(self) -> AuditLogRepository:
        if "audit_logs" not in self._repos:
            self._repos["audit_logs"] = AuditLogRepository(self.db)
        return self._repos["audit_logs"]
