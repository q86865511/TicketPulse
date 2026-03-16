"""KKTIX scraper — prefers JSON API endpoints over HTML parsing."""
from __future__ import annotations

import re
from datetime import datetime, timezone

from scraper.base import BaseScraper, TicketInfo, TicketStatus
from core.logger import get_logger

logger = get_logger(__name__)

# KKTIX event JSON endpoint pattern: https://kktix.com/events/{slug}.json
_SLUG_RE = re.compile(r"kktix\.com/events/([^/?#]+)")


class KKTIXScraper(BaseScraper):
    platform = "kktix"

    async def fetch(self, url: str) -> TicketInfo | None:
        slug_match = _SLUG_RE.search(url)
        if not slug_match:
            logger.warning("kktix_invalid_url", url=url)
            return None

        slug = slug_match.group(1)
        api_url = f"https://kktix.com/events/{slug}.json"

        try:
            data = await self._get_json(api_url)
        except Exception as exc:
            logger.error("kktix_fetch_failed", slug=slug, error=str(exc))
            raise

        return self._parse(data, url)

    def _parse(self, data: dict, original_url: str) -> TicketInfo:
        registration = data.get("registration", {})
        tickets = data.get("tickets", [])

        # Determine status
        status_str = registration.get("status", "")
        if status_str == "started":
            status = TicketStatus.AVAILABLE
        elif status_str == "ended":
            status = TicketStatus.SOLD_OUT
        elif status_str == "not_started":
            status = TicketStatus.COMING_SOON
        else:
            status = TicketStatus.UNKNOWN

        # Seat types & price range
        seat_types = [t.get("name", "") for t in tickets if t.get("name")]
        prices = [t.get("price", 0) for t in tickets if t.get("price")]
        price_range = {}
        if prices:
            price_range = {"min": min(prices), "max": max(prices)}

        # Date
        start_at = data.get("start_at")
        event_date: datetime | None = None
        if start_at:
            try:
                event_date = datetime.fromisoformat(start_at.replace("Z", "+00:00"))
            except ValueError:
                pass

        return TicketInfo(
            platform=self.platform,
            concert_id=str(data.get("id", "")),
            name=data.get("name", ""),
            artist=data.get("organizer", {}).get("name", ""),
            venue=data.get("venue", {}).get("name", ""),
            date=event_date,
            ticket_url=original_url,
            seat_types=seat_types,
            price_range=price_range,
            status=status,
        )
