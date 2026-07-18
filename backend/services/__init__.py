from services.locator import ServiceLocator
from services.organization_service import OrganizationService
from services.department_service import DepartmentService
from services.user_service import UserService
from services.auth_service import AuthService
from services.role_service import RoleService, PermissionService
from services.lead_service import LeadService

locator = ServiceLocator()

__all__ = [
    "ServiceLocator",
    "OrganizationService",
    "DepartmentService",
    "UserService",
    "AuthService",
    "RoleService",
    "PermissionService",
    "LeadService",
    "locator",
]


