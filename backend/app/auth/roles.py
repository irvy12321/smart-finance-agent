"""
Role-Based Access Control (RBAC) - Role and Permission Definitions

Roles:
- admin: Full access to all features
- analyst: Can use research, chat, tools, RAG
- viewer: Can only view reports and system status
"""
from enum import Enum


class Role(str, Enum):
    """User roles"""
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


# Permission definitions
PERMISSIONS = {
    "user:manage": "Manage users (create, update, delete)",
    "system:manage": "Manage system configuration",
    "task:create": "Create research tasks",
    "task:execute": "Execute research tasks",
    "chat:use": "Use AI chat",
    "rag:manage": "Manage RAG knowledge base",
    "rag:delete": "Delete RAG documents",
    "tools:use": "Use financial tools",
    "report:view": "View reports",
    "system:view": "View system status",
}

# Role-permission mapping
ROLE_PERMISSIONS: dict[Role, list[str]] = {
    Role.ADMIN: [
        "user:manage",
        "system:manage",
        "task:create",
        "task:execute",
        "chat:use",
        "rag:manage",
        "rag:delete",
        "tools:use",
        "report:view",
        "system:view",
    ],
    Role.ANALYST: [
        "task:create",
        "task:execute",
        "chat:use",
        "rag:manage",
        "tools:use",
        "report:view",
        "system:view",
    ],
    Role.VIEWER: [
        "report:view",
        "system:view",
    ],
}

# Valid roles for API endpoints
ROLES_ALL = [Role.ADMIN, Role.ANALYST, Role.VIEWER]
ROLES_WRITE = [Role.ADMIN, Role.ANALYST]
ROLES_ADMIN = [Role.ADMIN]


def get_role_permissions(role: str) -> list[str]:
    """Get permissions for a role"""
    try:
        r = Role(role)
        return ROLE_PERMISSIONS.get(r, [])
    except ValueError:
        return []


def has_permission(role: str, permission: str) -> bool:
    """Check if a role has a specific permission"""
    return permission in get_role_permissions(role)


def has_any_permission(role: str, permissions: list[str]) -> bool:
    """Check if a role has any of the specified permissions"""
    role_permissions = get_role_permissions(role)
    return any(p in role_permissions for p in permissions)


def has_all_permissions(role: str, permissions: list[str]) -> bool:
    """Check if a role has all of the specified permissions"""
    role_permissions = get_role_permissions(role)
    return all(p in role_permissions for p in permissions)


def is_valid_role(role: str) -> bool:
    """Check if a role string is valid"""
    try:
        Role(role)
        return True
    except ValueError:
        return False


def get_default_role() -> str:
    """Get the default role for new users"""
    return Role.VIEWER.value
