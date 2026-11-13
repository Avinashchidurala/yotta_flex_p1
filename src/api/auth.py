"""
Role-Based Access Control (RBAC) Module
Defines 4 primary actor roles and authorization middleware.
"""

from enum import Enum
from typing import Optional
from fastapi import Header, HTTPException, status


class Role(str, Enum):
    CUSTOMER = "customer"
    WAREHOUSE_OPERATOR = "operator"
    OPERATIONS_MANAGER = "manager"
    ANALYST = "analyst"


def get_current_role(x_role: Optional[str] = Header("analyst")) -> Role:
    """Extracts and validates actor role from X-Role header."""
    try:
        return Role(x_role.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Invalid actor role '{x_role}'. Allowed: {[r.value for r in Role]}"
        )


def require_role(*allowed_roles: Role):
    """Dependency that enforces endpoint-level RBAC."""
    def role_checker(current_role: Role = Header("analyst", alias="X-Role")):
        try:
            r = Role(current_role.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Invalid actor role '{current_role}'"
            )
        if r not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied for role '{r.value}'. Required one of: {[a.value for a in allowed_roles]}"
            )
        return r
    return role_checker

