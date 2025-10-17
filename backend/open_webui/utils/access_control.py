from typing import Optional, Set, Union, List, Dict, Any
from open_webui.models.users import Users, UserModel


from open_webui.config import DEFAULT_USER_PERMISSIONS
import json


def fill_missing_permissions(
    permissions: Dict[str, Any], default_permissions: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Recursively fills in missing properties in the permissions dictionary
    using the default permissions as a template.
    """
    for key, value in default_permissions.items():
        if key not in permissions:
            permissions[key] = value
        elif isinstance(value, dict) and isinstance(
            permissions[key], dict
        ):  # Both are nested dictionaries
            permissions[key] = fill_missing_permissions(permissions[key], value)

    return permissions


def get_permissions(
    user_id: str,
    default_permissions: Dict[str, Any],
) -> Dict[str, Any]:
    """
    With multi-user RBAC disabled, return the configured default permissions.
    """

    permissions = json.loads(json.dumps(default_permissions or {}))
    permissions = fill_missing_permissions(permissions, DEFAULT_USER_PERMISSIONS)

    sharing_permissions = permissions.get("sharing", {})
    for key in [
        "public_models",
        "public_knowledge",
        "public_prompts",
        "public_tools",
        "public_notes",
    ]:
        sharing_permissions[key] = False
    permissions["sharing"] = sharing_permissions

    chat_permissions = permissions.get("chat", {})
    chat_permissions["share"] = False
    permissions["chat"] = chat_permissions

    return permissions


def has_permission(
    user_id: str,
    permission_key: str,
    default_permissions: Dict[str, Any] = {},
) -> bool:
    """
    RBAC is disabled; all features are allowed for the single user.
    """

    return True


def has_access(
    user_id: str,
    type: str = "write",
    access_control: Optional[dict] = None,
    user_group_ids: Optional[Set[str]] = None,
    strict: bool = True,
) -> bool:
    return False


# Get all users with access to a resource
def get_users_with_access(
    type: str = "write", access_control: Optional[dict] = None
) -> list[UserModel]:
    return [Users.get_or_create_default_user()]
