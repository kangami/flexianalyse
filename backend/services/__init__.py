from services.locator import ServiceLocator
from services.organization_service import OrganizationService
from services.department_service import DepartmentService
from services.user_service import UserService
from services.role_service import RoleService, PermissionService

locator = ServiceLocator()

__all__ = [
    "ServiceLocator",
    "OrganizationService",
    "DepartmentService",
    "UserService",
    "RoleService",
    "PermissionService",
    "locator",
]


