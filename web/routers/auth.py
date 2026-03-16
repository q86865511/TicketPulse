"""Discord OAuth2 login flow."""
from __future__ import annotations

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from starlette.config import Config

import db.crud as crud
from core.config import settings
from core.logger import get_logger
from db.session import get_db

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

_config = Config()
oauth = OAuth(_config)
oauth.register(
    name="discord",
    client_id=settings.discord_client_id,
    client_secret=settings.discord_client_secret,
    authorize_url="https://discord.com/api/oauth2/authorize",
    access_token_url="https://discord.com/api/oauth2/token",
    api_base_url="https://discord.com/api/",
    client_kwargs={"scope": "identify email"},
)


@router.get("/login")
async def login(request: Request) -> RedirectResponse:
    return await oauth.discord.authorize_redirect(request, settings.discord_redirect_uri)


@router.get("/callback")
async def callback(request: Request) -> RedirectResponse:
    token = await oauth.discord.authorize_access_token(request)
    resp = await oauth.discord.get("users/@me", token=token)
    discord_user = resp.json()

    async for db in get_db():
        user = await crud.get_user_by_discord_id(db, str(discord_user["id"]))
        if not user:
            user = await crud.create_user(
                db,
                discord_id=str(discord_user["id"]),
                username=discord_user.get("username", ""),
                avatar_url=f"https://cdn.discordapp.com/avatars/{discord_user['id']}/{discord_user.get('avatar')}.png"
                if discord_user.get("avatar")
                else None,
                email=discord_user.get("email"),
            )
        else:
            # Update email if newly granted
            if discord_user.get("email") and not user.email:
                await crud.update_user_preferences(db, user.id, email=discord_user["email"])

    request.session["user_id"] = str(discord_user["id"])
    request.session["username"] = discord_user.get("username", "")
    avatar = discord_user.get("avatar")
    request.session["avatar_url"] = (
        f"https://cdn.discordapp.com/avatars/{discord_user['id']}/{avatar}.png"
        if avatar else ""
    )
    logger.info("user_logged_in", discord_id=discord_user["id"])
    return RedirectResponse(url="/")


@router.get("/logout")
async def logout(request: Request) -> RedirectResponse:
    request.session.clear()
    return RedirectResponse(url="/")


@router.get("/session")
async def session_info(request: Request) -> dict:
    """Return minimal session info for frontend JS."""
    return {
        "logged_in": bool(request.session.get("user_id")),
        "user_id": request.session.get("user_id"),
        "username": request.session.get("username"),
        "avatar_url": request.session.get("avatar_url"),
    }


@router.get("/me")
async def me(request: Request) -> dict:
    discord_id = request.session.get("user_id")
    if not discord_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    async for db in get_db():
        user = await crud.get_user_by_discord_id(db, discord_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return {
            "id": user.id,
            "discord_id": user.discord_id,
            "username": user.username,
            "avatar_url": user.avatar_url,
            "email": user.email,
            "notification_preference": user.notification_preference.value,
            "profile_visibility": user.profile_visibility.value,
        }
