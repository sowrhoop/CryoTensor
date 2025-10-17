import logging
from typing import Optional

from pydantic import BaseModel, ConfigDict

from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


class GroupForm(BaseModel):
    name: str
    description: str
    permissions: Optional[dict] = None


class UserIdsForm(BaseModel):
    user_ids: Optional[list[str]] = None


class GroupUpdateForm(GroupForm, UserIdsForm):
    pass


class GroupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    name: str
    description: str
    permissions: Optional[dict] = None
    data: Optional[dict] = None
    meta: Optional[dict] = None
    user_ids: list[str] = []
    created_at: Optional[int] = None
    updated_at: Optional[int] = None


class GroupsTable:
    """
    Multi-user group management is disabled in the single-user build, so these
    helpers return empty results and act as no-ops.
    """

    def get_groups(self) -> list[GroupResponse]:
        return []

    def get_groups_by_member_id(self, user_id: str) -> list[GroupResponse]:
        return []

    def get_group_by_id(self, id: str) -> Optional[GroupResponse]:
        return None

    def insert_new_group(
        self, user_id: str, form_data: GroupForm
    ) -> Optional[GroupResponse]:
        log.info("Group creation requested but groups feature is disabled.")
        return None

    def update_group_by_id(
        self, id: str, form_data: GroupUpdateForm
    ) -> Optional[GroupResponse]:
        log.info("Group update requested but groups feature is disabled.")
        return None

    def add_users_to_group(
        self, id: str, user_ids: Optional[list[str]]
    ) -> Optional[GroupResponse]:
        return None

    def remove_users_from_group(
        self, id: str, user_ids: Optional[list[str]]
    ) -> Optional[GroupResponse]:
        return None

    def delete_group_by_id(self, id: str) -> bool:
        return False

    def delete_all_groups(self) -> bool:
        return True

    def get_group_user_ids_by_id(self, id: str) -> Optional[list[str]]:
        return []

    def remove_user_from_all_groups(self, user_id: str) -> bool:
        return True


Groups = GroupsTable()
