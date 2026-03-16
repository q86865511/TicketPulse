"""
Notification dispatcher — supports Discord DM, Discord channel, Email (SMTP or SendGrid).
All public methods are async-safe and fire-and-forget friendly.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from core.config import settings
from core.logger import get_logger

if TYPE_CHECKING:
    import discord as _discord

logger = get_logger(__name__)


class NotificationMethod(str, Enum):
    DISCORD_DM = "discord_dm"
    DISCORD_CHANNEL = "discord_channel"
    EMAIL = "email"
    BOTH = "both"  # Discord DM + Email


@dataclass
class NotificationPayload:
    subject: str          # Used as email subject / Discord embed title
    body: str             # Plain-text fallback
    html_body: str = ""   # Rich HTML for email
    embed: object = None  # discord.Embed instance (optional)


class Notifier:
    def __init__(self, bot: "_discord.Client | None" = None) -> None:
        self._bot = bot

    # ──────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────

    async def send(
        self,
        method: NotificationMethod,
        payload: NotificationPayload,
        *,
        discord_user_id: int | None = None,
        discord_channel_id: int | None = None,
        email_address: str | None = None,
    ) -> None:
        """Dispatch a notification via the requested channel(s)."""
        tasks: list[asyncio.coroutine] = []

        if method in (NotificationMethod.DISCORD_DM, NotificationMethod.BOTH):
            if discord_user_id and self._bot:
                tasks.append(self._send_discord_dm(discord_user_id, payload))

        if method == NotificationMethod.DISCORD_CHANNEL:
            if discord_channel_id and self._bot:
                tasks.append(self._send_discord_channel(discord_channel_id, payload))

        if method in (NotificationMethod.EMAIL, NotificationMethod.BOTH):
            if email_address:
                tasks.append(self._send_email(email_address, payload))

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, Exception):
                    logger.error("notification_failed", error=str(r))

    # ──────────────────────────────────────────────────────────
    # Discord
    # ──────────────────────────────────────────────────────────

    async def _send_discord_dm(self, user_id: int, payload: NotificationPayload) -> None:
        assert self._bot is not None
        try:
            user = await self._bot.fetch_user(user_id)
            if payload.embed:
                await user.send(embed=payload.embed)
            else:
                await user.send(content=payload.body)
            logger.info("discord_dm_sent", user_id=user_id)
        except Exception as exc:
            logger.error("discord_dm_failed", user_id=user_id, error=str(exc))
            raise

    async def _send_discord_channel(self, channel_id: int, payload: NotificationPayload) -> None:
        assert self._bot is not None
        try:
            channel = self._bot.get_channel(channel_id) or await self._bot.fetch_channel(channel_id)
            if payload.embed:
                await channel.send(embed=payload.embed)  # type: ignore[union-attr]
            else:
                await channel.send(content=payload.body)  # type: ignore[union-attr]
            logger.info("discord_channel_sent", channel_id=channel_id)
        except Exception as exc:
            logger.error("discord_channel_failed", channel_id=channel_id, error=str(exc))
            raise

    # ──────────────────────────────────────────────────────────
    # Email
    # ──────────────────────────────────────────────────────────

    async def _send_email(self, to_address: str, payload: NotificationPayload) -> None:
        if settings.sendgrid_api_key:
            await self._send_via_sendgrid(to_address, payload)
        else:
            await self._send_via_smtp(to_address, payload)

    async def _send_via_smtp(self, to_address: str, payload: NotificationPayload) -> None:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = payload.subject
        msg["From"] = settings.email_from
        msg["To"] = to_address

        msg.attach(MIMEText(payload.body, "plain", "utf-8"))
        if payload.html_body:
            msg.attach(MIMEText(payload.html_body, "html", "utf-8"))

        try:
            await aiosmtplib.send(
                msg,
                hostname=settings.email_host,
                port=settings.email_port,
                username=settings.email_username,
                password=settings.email_password,
                start_tls=True,
            )
            logger.info("email_smtp_sent", to=to_address)
        except Exception as exc:
            logger.error("email_smtp_failed", to=to_address, error=str(exc))
            raise

    async def _send_via_sendgrid(self, to_address: str, payload: NotificationPayload) -> None:
        import aiohttp

        data = {
            "personalizations": [{"to": [{"email": to_address}]}],
            "from": {"email": settings.email_from},
            "subject": payload.subject,
            "content": [
                {"type": "text/plain", "value": payload.body},
            ],
        }
        if payload.html_body:
            data["content"].append({"type": "text/html", "value": payload.html_body})

        headers = {
            "Authorization": f"Bearer {settings.sendgrid_api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.sendgrid.com/v3/mail/send",
                    json=data,
                    headers=headers,
                ) as resp:
                    if resp.status not in (200, 202):
                        body = await resp.text()
                        raise RuntimeError(f"SendGrid error {resp.status}: {body}")
            logger.info("email_sendgrid_sent", to=to_address)
        except Exception as exc:
            logger.error("email_sendgrid_failed", to=to_address, error=str(exc))
            raise
