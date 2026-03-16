"""
APScheduler job definitions.
The scheduler polls all active ScraperState entries and fires alerts on changes.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from apscheduler.schedulers.asyncio import AsyncIOScheduler

import db.crud as crud
from core.config import settings
from core.logger import get_logger
from core.notifier import NotificationMethod, NotificationPayload, Notifier
from db.models import AlertType, TicketPlatform
from db.session import AsyncSessionLocal
from scraper.base import BaseScraper, TicketStatus
from scraper.kktix import KKTIXScraper
from scraper.tixcraft import TixCraftScraper
from scraper.ticket_plus import TicketPlusScraper
from scraper.ibon import IbonScraper
from scraper.kham import KhamScraper

if TYPE_CHECKING:
    import discord as _discord

logger = get_logger(__name__)

_SCRAPERS: dict[TicketPlatform, BaseScraper] = {
    TicketPlatform.KKTIX: KKTIXScraper(poll_interval_seconds=settings.scraper_interval_seconds),
    TicketPlatform.TIXCRAFT: TixCraftScraper(poll_interval_seconds=settings.scraper_interval_seconds * 2),
    TicketPlatform.TICKET_PLUS: TicketPlusScraper(poll_interval_seconds=settings.scraper_interval_seconds),
    TicketPlatform.IBON: IbonScraper(poll_interval_seconds=settings.scraper_interval_seconds),
    TicketPlatform.KHAM: KhamScraper(poll_interval_seconds=settings.scraper_interval_seconds),
}


async def run_scraper_job(notifier: Notifier) -> None:
    """Main scraper job — iterates all active concerts and dispatches alerts."""
    async with AsyncSessionLocal() as db:
        states = await crud.get_active_scraper_states(db)

    for state in states:
        async with AsyncSessionLocal() as db:
            concert = await crud.get_concert_by_id(db, state.concert_id)
            if not concert:
                continue

            scraper = _SCRAPERS.get(state.platform)
            if not scraper:
                continue

            info = await scraper.poll(concert.ticket_url)
            if not info:
                await crud.upsert_scraper_state(
                    db,
                    platform=state.platform,
                    concert_id=concert.id,
                    last_seen_hash=state.last_seen_hash,
                    last_checked_at=datetime.now(tz=timezone.utc),
                    consecutive_failures=state.consecutive_failures + 1,
                )
                await db.commit()
                continue

            new_hash = info.content_hash()
            if new_hash == state.last_seen_hash:
                # No change — update timestamp only
                await crud.upsert_scraper_state(
                    db,
                    platform=state.platform,
                    concert_id=concert.id,
                    last_seen_hash=new_hash,
                    last_checked_at=datetime.now(tz=timezone.utc),
                    consecutive_failures=0,
                )
                await db.commit()
                continue

            # Content changed — determine alert type
            alert_type = _determine_alert_type(info)
            if alert_type and not await crud.has_recent_alert(db, concert.id, alert_type):
                users = await crud.get_watching_users_for_concert(db, concert.id)
                await _dispatch_alerts(notifier, concert, info, alert_type, users)
                await crud.create_alert_log(db, concert.id, alert_type, len(users))

            await crud.upsert_scraper_state(
                db,
                platform=state.platform,
                concert_id=concert.id,
                last_seen_hash=new_hash,
                last_checked_at=datetime.now(tz=timezone.utc),
                consecutive_failures=0,
            )
            await db.commit()
            logger.info("scraper_state_updated", concert_id=concert.id, alert_type=alert_type)


def _determine_alert_type(info) -> AlertType | None:
    if info.status == TicketStatus.AVAILABLE:
        return AlertType.FIRST_DROP
    return None


async def _dispatch_alerts(notifier, concert, info, alert_type, users) -> None:
    import discord as _discord

    price_str = ""
    if info.price_range:
        price_str = f"NT${info.price_range.get('min', 0):,.0f} – NT${info.price_range.get('max', 0):,.0f}"

    subject = f"[TicketPulse] 票券開賣：{concert.name}"
    body = (
        f"《{concert.name}》票券現已開放購票！\n"
        f"場地：{concert.venue}\n"
        f"票價：{price_str or '請見售票網站'}\n"
        f"購票連結：{concert.ticket_url}"
    )
    html_body = f"""
    <h2>{concert.name} — 票券開賣！</h2>
    <p><strong>場地：</strong>{concert.venue}</p>
    <p><strong>票價：</strong>{price_str or '請見售票網站'}</p>
    <p><a href="{concert.ticket_url}">立即購票</a></p>
    """

    embed = _discord.Embed(
        title=f"🎫 {concert.name}",
        description="票券現已開放購票！",
        color=_discord.Color.green(),
        url=concert.ticket_url,
    )
    embed.add_field(name="場地", value=concert.venue, inline=True)
    if price_str:
        embed.add_field(name="票價", value=price_str, inline=True)
    embed.add_field(name="購票連結", value=f"[點此購票]({concert.ticket_url})", inline=False)

    payload = NotificationPayload(subject=subject, body=body, html_body=html_body, embed=embed)

    tasks = []
    for user in users:
        tasks.append(notifier.send(
            method=NotificationMethod(user.notification_preference),
            payload=payload,
            discord_user_id=int(user.discord_id),
            email_address=user.email,
        ))
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


def create_scheduler(notifier: Notifier) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_scraper_job,
        "interval",
        seconds=settings.scraper_interval_seconds,
        args=[notifier],
        id="ticket_scraper",
        max_instances=1,
        coalesce=True,
    )
    return scheduler
