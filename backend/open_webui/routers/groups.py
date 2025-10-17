import logging

from open_webui.models.groups import (
    GroupForm,
    GroupUpdateForm,
    GroupResponse,
    UserIdsForm,
)

from open_webui.constants import ERROR_MESSAGES
from fastapi import APIRouter, Depends, HTTPException, status

from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.env import SRC_LOG_LEVELS


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])

router = APIRouter()

############################
# GetFunctions
############################


@router.get("/", response_model=list[GroupResponse])
async def get_groups(user=Depends(get_verified_user)):
    return []


############################
# CreateNewGroup
############################


@router.post("/create", response_model=Optional[GroupResponse])
async def create_new_group(form_data: GroupForm, user=Depends(get_admin_user)):
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Groups are disabled in single-user mode.",
    )


############################
# GetGroupById
############################


@router.get("/id/{id}", response_model=Optional[GroupResponse])
async def get_group_by_id(id: str, user=Depends(get_admin_user)):
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=ERROR_MESSAGES.NOT_FOUND,
    )


############################
# UpdateGroupById
############################


@router.post("/id/{id}/update", response_model=Optional[GroupResponse])
async def update_group_by_id(
    id: str, form_data: GroupUpdateForm, user=Depends(get_admin_user)
):
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Groups are disabled in single-user mode.",
    )


############################
# AddUserToGroupByUserIdAndGroupId
############################


@router.post("/id/{id}/users/add", response_model=Optional[GroupResponse])
async def add_user_to_group(
    id: str, form_data: UserIdsForm, user=Depends(get_admin_user)
):
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Groups are disabled in single-user mode.",
    )


@router.post("/id/{id}/users/remove", response_model=Optional[GroupResponse])
async def remove_users_from_group(
    id: str, form_data: UserIdsForm, user=Depends(get_admin_user)
):
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Groups are disabled in single-user mode.",
    )


############################
# DeleteGroupById
############################


@router.delete("/id/{id}/delete", response_model=bool)
async def delete_group_by_id(id: str, user=Depends(get_admin_user)):
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Groups are disabled in single-user mode.",
    )
