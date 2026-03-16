"""
Discord HTTP Interactions endpoint.

Every slash command invocation from Discord is delivered here as a POST request.
This module:
  1. Verifies the Ed25519 signature using DISCORD_PUBLIC_KEY
  2. Responds to PING (type 1) with PONG
  3. Handles application commands (type 2)

Register this URL in Discord Developer Portal:
  General Information → Interactions Endpoint URL → https://<your-domain>/interactions
"""
from __future__ import annotations

import hashlib
import hmac

from fastapi import APIRouter, HTTPException, Request, Response
from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey

import db.crud as crud
from core.config import settings
from core.logger import get_logger
from db.session import AsyncSessionLocal

logger = get_logger(__name__)
router = APIRouter(tags=["interactions"])

# Discord Interaction types
PING = 1
APPLICATION_COMMAND = 2
MESSAGE_COMPONENT = 3

# Discord response types
PONG = 1
CHANNEL_MESSAGE_WITH_SOURCE = 4
DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE = 5


def _verify_signature(signature: str, timestamp: str, body: bytes) -> bool:
    """Verify Discord's Ed25519 request signature."""
    try:
        vk = VerifyKey(bytes.fromhex(settings.discord_public_key))
        vk.verify((timestamp.encode() + body), bytes.fromhex(signature))
        return True
    except (BadSignatureError, Exception):
        return False


def _message(content: str, ephemeral: bool = True) -> dict:
    return {
        "type": CHANNEL_MESSAGE_WITH_SOURCE,
        "data": {
            "content": content,
            "flags": 64 if ephemeral else 0,
        },
    }


def _embed_message(embed: dict, ephemeral: bool = True) -> dict:
    return {
        "type": CHANNEL_MESSAGE_WITH_SOURCE,
        "data": {
            "embeds": [embed],
            "flags": 64 if ephemeral else 0,
        },
    }


@router.post("/interactions")
async def interactions(request: Request) -> Response:
    # ── Signature verification ──────────────────────────────
    signature = request.headers.get("X-Signature-Ed25519", "")
    timestamp = request.headers.get("X-Signature-Timestamp", "")
    body = await request.body()

    if not signature or not timestamp or not _verify_signature(signature, timestamp, body):
        logger.warning("interactions_invalid_signature", sig=signature[:16])
        raise HTTPException(status_code=401, detail="Invalid request signature")

    # ── Parse payload ───────────────────────────────────────
    payload = await request.json()
    interaction_type = payload.get("type")

    # PING — Discord health check (must respond immediately)
    if interaction_type == PING:
        return Response(content='{"type":1}', media_type="application/json")

    # Application commands
    if interaction_type == APPLICATION_COMMAND:
        return await _handle_command(payload)

    raise HTTPException(status_code=400, detail="Unsupported interaction type")


async def _handle_command(payload: dict) -> Response:
    import json

    data = payload.get("data", {})
    command_name = data.get("name", "")
    discord_user = (payload.get("member") or {}).get("user") or payload.get("user") or {}
    discord_id = discord_user.get("id", "")

    logger.info("interaction_command", command=command_name, discord_id=discord_id)

    match command_name:
        case "status":
            response = await _cmd_status(discord_id)
        case "watchlist":
            response = await _cmd_watchlist(discord_id)
        case "link":
            response = _cmd_link()
        case "alert-test":
            response = await _cmd_alert_test(payload, discord_id)
        case _:
            response = _message("未知指令。請至網頁版管理所有功能。")

    from fastapi.responses import JSONResponse
    return JSONResponse(content=response)


# ──────────────────────────────────────────────
# Command handlers
# ──────────────────────────────────────────────

async def _cmd_status(discord_id: str) -> dict:
    if not discord_id:
        return _message("無法取得你的 Discord 帳號資訊。")

    async with AsyncSessionLocal() as db:
        user = await crud.get_user_by_discord_id(db, discord_id)

    if not user:
        return _embed_message({
            "title": "❌ 尚未連結",
            "description": (
                "你的 Discord 帳號尚未連結 TicketPulse。\n\n"
                f"請前往 **[{settings.app_base_url}]({settings.app_base_url})** 使用 Discord 登入。"
            ),
            "color": 0xED4245,
        })

    watchlist_count = len(await _get_watchlist_count(db, user.id))
    return _embed_message({
        "title": "✅ 已連結 TicketPulse",
        "description": f"歡迎回來，**{user.username}**！",
        "fields": [
            {"name": "通知方式", "value": user.notification_preference.value, "inline": True},
            {"name": "關注中演唱會", "value": str(watchlist_count), "inline": True},
            {"name": "管理設定", "value": f"[前往網頁]({settings.app_base_url}/settings)", "inline": False},
        ],
        "color": 0x57F287,
    })


async def _get_watchlist_count(db, user_id: int) -> list:
    items = await crud.get_watchlist(db, user_id)
    return items


async def _cmd_watchlist(discord_id: str) -> dict:
    if not discord_id:
        return _message("無法取得你的 Discord 帳號資訊。")

    async with AsyncSessionLocal() as db:
        user = await crud.get_user_by_discord_id(db, discord_id)
        if not user:
            return _message(
                f"請先至 {settings.app_base_url} 登入，再使用此指令。"
            )
        items = await crud.get_watchlist(db, user.id)

    if not items:
        return _embed_message({
            "title": "🎯 你的關注清單",
            "description": (
                "目前沒有任何關注的演唱會。\n\n"
                f"[點此前往網頁版新增]({settings.app_base_url}/watchlist)"
            ),
            "color": 0x5865F2,
        })

    fields = []
    for item in items[:5]:
        status_emoji = {"watching": "👀", "notified": "🔔", "expired": "💤"}.get(
            item.status.value, "👀"
        )
        fields.append({
            "name": f"{status_emoji} {item.concert.name}",
            "value": f"場地：{item.concert.venue or '-'}",
            "inline": False,
        })

    if len(items) > 5:
        fields.append({
            "name": f"...還有 {len(items) - 5} 筆",
            "value": f"[查看全部]({settings.app_base_url}/watchlist)",
            "inline": False,
        })

    return _embed_message({
        "title": f"🎯 關注清單（共 {len(items)} 筆）",
        "fields": fields,
        "color": 0x5865F2,
        "footer": {"text": f"在網頁版管理完整清單：{settings.app_base_url}/watchlist"},
    })


def _cmd_link() -> dict:
    return _embed_message({
        "title": "🌐 TicketPulse 網頁版",
        "description": (
            f"點此前往 TicketPulse 網頁版：\n**{settings.app_base_url}**\n\n"
            "網頁版提供完整功能：\n"
            "• 新增 / 移除關注清單\n"
            "• 演唱會歷史紀錄\n"
            "• 好友系統\n"
            "• 通知設定與隱私設定"
        ),
        "color": 0xFEE75C,
    })


async def _cmd_alert_test(payload: dict, discord_id: str) -> dict:
    # Admin-only: check for MANAGE_GUILD permission
    member = payload.get("member", {})
    permissions = int(member.get("permissions", "0"))
    MANAGE_GUILD = 1 << 5
    if not (permissions & MANAGE_GUILD):
        return _message("此指令需要「管理伺服器」權限。", ephemeral=True)

    return _embed_message({
        "title": "🎫 測試通知",
        "description": "TicketPulse 通知系統運作正常！\n這是一則測試訊息。",
        "color": 0x57F287,
    })
