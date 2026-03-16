"""Concert history REST endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

import db.crud as crud
from db.models import ConcertHistoryStatus, TicketPlatform
from db.session import get_db

router = APIRouter(prefix="/history", tags=["history"])


def _require_session(request: Request) -> str:
    discord_id = request.session.get("user_id")
    if not discord_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return discord_id


class HistoryAddRequest(BaseModel):
    concert_name: str
    artist: str
    venue: str
    status: str = "attended"
    notes: str | None = None


@router.get("/")
async def list_history(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    discord_id = _require_session(request)
    user = await crud.get_user_by_discord_id(db, discord_id)
    if not user:
        return []
    entries = await crud.get_concert_history(db, user.id)
    return [
        {
            "id": e.id,
            "status": e.status.value,
            "notes": e.notes,
            "logged_at": e.logged_at.isoformat(),
            "concert": {
                "id": e.concert.id,
                "name": e.concert.name,
                "artist": e.concert.artist,
                "venue": e.concert.venue,
            },
        }
        for e in entries
    ]


@router.post("/")
async def add_history(
    body: HistoryAddRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    discord_id = _require_session(request)
    user = await crud.get_user_by_discord_id(db, discord_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    concert = await crud.create_concert(
        db,
        name=body.concert_name,
        artist=body.artist,
        venue=body.venue,
        city="",
        ticket_url="",
        platform=TicketPlatform.KKTIX,
    )
    entry = await crud.add_concert_history(
        db,
        user_id=user.id,
        concert_id=concert.id,
        status=ConcertHistoryStatus(body.status),
        notes=body.notes,
    )
    return {"id": entry.id, "concert_id": concert.id, "status": entry.status.value}
