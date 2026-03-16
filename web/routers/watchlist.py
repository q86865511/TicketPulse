"""Watchlist REST endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

import db.crud as crud
from db.session import get_db
from bot.cogs.watchlist import _detect_platform, _SCRAPER_MAP

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


def _require_session(request: Request) -> str:
    discord_id = request.session.get("user_id")
    if not discord_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return discord_id


class WatchlistAddRequest(BaseModel):
    url: str


@router.get("/")
async def list_watchlist(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    discord_id = _require_session(request)
    user = await crud.get_user_by_discord_id(db, discord_id)
    if not user:
        return []
    items = await crud.get_watchlist(db, user.id)
    return [
        {
            "id": item.id,
            "status": item.status.value,
            "added_at": item.added_at.isoformat(),
            "concert": {
                "id": item.concert.id,
                "name": item.concert.name,
                "artist": item.concert.artist,
                "venue": item.concert.venue,
                "date": item.concert.date.isoformat() if item.concert.date else None,
                "ticket_url": item.concert.ticket_url,
                "platform": item.concert.platform.value,
            },
        }
        for item in items
    ]


@router.post("/")
async def add_watchlist_item(
    body: WatchlistAddRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    discord_id = _require_session(request)
    user = await crud.get_user_by_discord_id(db, discord_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    platform = _detect_platform(body.url)
    if not platform:
        raise HTTPException(status_code=400, detail="不支援的售票平台，請確認網址是否來自 KKTIX、TixCraft、拓元、ibon 或寬宏藝術")

    scraper = _SCRAPER_MAP[platform]
    info = await scraper.fetch(body.url)
    if not info:
        raise HTTPException(status_code=422, detail="無法取得演唱會資訊，請確認網址是否正確")

    concert = await crud.create_concert(
        db,
        name=info.name,
        artist=info.artist,
        venue=info.venue,
        city="",
        ticket_url=body.url,
        platform=platform,
        date=info.date,
        seat_types=info.seat_types,
        min_price=info.price_range.get("min"),
        max_price=info.price_range.get("max"),
    )
    existing = await crud.get_watchlist_item(db, user.id, concert.id)
    if existing:
        raise HTTPException(status_code=409, detail="此演唱會已在關注清單中")

    item = await crud.add_to_watchlist(db, user.id, concert.id)
    return {"id": item.id, "concert_name": concert.name, "status": item.status.value}


@router.delete("/{item_id}")
async def remove_watchlist_item(
    item_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    discord_id = _require_session(request)
    user = await crud.get_user_by_discord_id(db, discord_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    removed = await crud.remove_from_watchlist(db, user.id, item_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Watchlist item not found")
    return {"detail": "removed"}
