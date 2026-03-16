"""Profile & friends REST endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

import db.crud as crud
from db.models import FriendshipStatus, NotificationPreference, ProfileVisibility
from db.session import get_db

router = APIRouter(prefix="/profile", tags=["profile"])


def _require_session(request: Request) -> str:
    discord_id = request.session.get("user_id")
    if not discord_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return discord_id


class PreferencesUpdateRequest(BaseModel):
    notification_preference: str | None = None
    profile_visibility: str | None = None
    quiet_hours_start: int | None = None
    quiet_hours_end: int | None = None
    email: str | None = None


@router.get("/{discord_id}")
async def get_profile(
    discord_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    viewer_discord_id = request.session.get("user_id")
    target = await crud.get_user_by_discord_id(db, discord_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    self_view = viewer_discord_id == discord_id
    if not self_view:
        if target.profile_visibility == ProfileVisibility.PRIVATE:
            raise HTTPException(status_code=403, detail="Profile is private")
        if target.profile_visibility == ProfileVisibility.FRIENDS:
            if not viewer_discord_id:
                raise HTTPException(status_code=403, detail="Profile is friends-only")
            viewer = await crud.get_user_by_discord_id(db, viewer_discord_id)
            if not viewer:
                raise HTTPException(status_code=403, detail="Profile is friends-only")
            friendship = await crud.get_friendship(db, viewer.id, target.id)
            if not friendship or friendship.status != FriendshipStatus.ACCEPTED:
                raise HTTPException(status_code=403, detail="Profile is friends-only")

    history = await crud.get_concert_history(db, target.id)
    watchlist = await crud.get_watchlist(db, target.id)

    return {
        "id": target.id,
        "discord_id": target.discord_id,
        "username": target.username,
        "avatar_url": target.avatar_url,
        "profile_visibility": target.profile_visibility.value,
        "history_count": len(history),
        "watching_count": sum(1 for w in watchlist if w.status.value == "watching"),
        "concert_history": [
            {
                "concert_name": e.concert.name,
                "status": e.status.value,
                "logged_at": e.logged_at.isoformat(),
            }
            for e in history
        ],
    }


@router.patch("/me/preferences")
async def update_preferences(
    body: PreferencesUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    discord_id = _require_session(request)
    user = await crud.get_user_by_discord_id(db, discord_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await crud.update_user_preferences(
        db,
        user.id,
        notification_preference=NotificationPreference(body.notification_preference)
        if body.notification_preference
        else None,
        profile_visibility=ProfileVisibility(body.profile_visibility)
        if body.profile_visibility
        else None,
        quiet_hours_start=body.quiet_hours_start,
        quiet_hours_end=body.quiet_hours_end,
        email=body.email,
    )
    return {"detail": "updated"}


@router.post("/friends/request/{target_discord_id}")
async def send_friend_request(
    target_discord_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    discord_id = _require_session(request)
    requester = await crud.get_user_by_discord_id(db, discord_id)
    receiver = await crud.get_user_by_discord_id(db, target_discord_id)
    if not requester or not receiver:
        raise HTTPException(status_code=404, detail="User not found")
    if requester.id == receiver.id:
        raise HTTPException(status_code=400, detail="Cannot send friend request to yourself")
    friendship = await crud.send_friend_request(db, requester.id, receiver.id)
    if not friendship:
        raise HTTPException(status_code=409, detail="Friend request already exists")
    return {"detail": "friend_request_sent", "friendship_id": friendship.id}


@router.post("/friends/accept/{friendship_id}")
async def accept_friend_request(
    friendship_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    discord_id = _require_session(request)
    user = await crud.get_user_by_discord_id(db, discord_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    friendship = await crud.accept_friend_request(db, friendship_id, user.id)
    if not friendship:
        raise HTTPException(status_code=404, detail="Friendship request not found")
    return {"detail": "accepted"}


@router.get("/me/friends")
async def list_friends(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    discord_id = _require_session(request)
    user = await crud.get_user_by_discord_id(db, discord_id)
    if not user:
        return []
    friends = await crud.get_friends(db, user.id)
    return [
        {
            "id": f.id,
            "discord_id": f.discord_id,
            "username": f.username,
            "avatar_url": f.avatar_url,
        }
        for f in friends
    ]
