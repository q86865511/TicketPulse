"""
Abstract scraper base class.
All platform scrapers must extend BaseScraper and implement `fetch()`.
Circuit-breaker and deduplication logic live here.
"""
from __future__ import annotations

import asyncio
import hashlib
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import ClassVar

import aiohttp
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from core.logger import get_logger

logger = get_logger(__name__)

CIRCUIT_BREAKER_THRESHOLD = 5  # Pause platform after this many consecutive failures


class TicketStatus(str, Enum):
    AVAILABLE = "available"
    SOLD_OUT = "sold_out"
    COMING_SOON = "coming_soon"
    UNKNOWN = "unknown"


@dataclass
class TicketInfo:
    platform: str
    concert_id: str          # Platform-side external ID
    name: str
    artist: str
    venue: str
    date: datetime | None
    ticket_url: str
    seat_types: list[str] = field(default_factory=list)
    price_range: dict[str, float] = field(default_factory=dict)  # {"min": 0, "max": 0}
    status: TicketStatus = TicketStatus.UNKNOWN

    def content_hash(self) -> str:
        """SHA-256 of the fields that matter for deduplication."""
        payload = f"{self.status}|{self.seat_types}|{self.price_range}"
        return hashlib.sha256(payload.encode()).hexdigest()


class BaseScraper(ABC):
    platform: ClassVar[str] = "base"
    # Realistic browser User-Agent headers
    DEFAULT_HEADERS: ClassVar[dict[str, str]] = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept": "text/html,application/xhtml+xml,application/json,*/*;q=0.8",
    }

    def __init__(self, poll_interval_seconds: int = 60, jitter_pct: float = 0.2) -> None:
        self.poll_interval = poll_interval_seconds
        self.jitter_pct = jitter_pct
        self._consecutive_failures = 0
        self._session: aiohttp.ClientSession | None = None

    # ──────────────────────────────────────────────
    # Abstract interface
    # ──────────────────────────────────────────────

    @abstractmethod
    async def fetch(self, url: str) -> TicketInfo | None:
        """
        Fetch ticket info from the given URL.
        Return None if the page is unavailable or the event is not found.
        """
        ...

    # ──────────────────────────────────────────────
    # HTTP helpers
    # ──────────────────────────────────────────────

    async def get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(headers=self.DEFAULT_HEADERS)
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    @retry(
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def _get(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        session = await self.get_session()
        resp = await session.get(url, timeout=aiohttp.ClientTimeout(total=15), **kwargs)
        resp.raise_for_status()
        return resp

    async def _get_json(self, url: str, **kwargs) -> dict:
        resp = await self._get(url, **kwargs)
        return await resp.json(content_type=None)

    async def _get_text(self, url: str, **kwargs) -> str:
        resp = await self._get(url, **kwargs)
        return await resp.text()

    # ──────────────────────────────────────────────
    # Poll with circuit-breaker & jitter
    # ──────────────────────────────────────────────

    async def poll(self, url: str) -> TicketInfo | None:
        """
        Single poll with circuit-breaker logic.
        Returns None and increments failure counter on error.
        """
        if self._consecutive_failures >= CIRCUIT_BREAKER_THRESHOLD:
            logger.warning(
                "scraper_circuit_open",
                platform=self.platform,
                failures=self._consecutive_failures,
            )
            return None

        jitter = random.uniform(-self.jitter_pct, self.jitter_pct) * self.poll_interval
        await asyncio.sleep(max(0, jitter))

        try:
            info = await self.fetch(url)
            self._consecutive_failures = 0
            logger.info("scraper_poll_ok", platform=self.platform, url=url, status=info.status if info else None)
            return info
        except Exception as exc:
            self._consecutive_failures += 1
            logger.error(
                "scraper_poll_failed",
                platform=self.platform,
                url=url,
                error=str(exc),
                consecutive_failures=self._consecutive_failures,
            )
            return None

    def reset_circuit(self) -> None:
        self._consecutive_failures = 0
