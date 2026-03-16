"""Ticket Plus (拓元) scraper — AJAX-driven, paginated event listing."""
from __future__ import annotations

import re
from datetime import datetime

from bs4 import BeautifulSoup

from scraper.base import BaseScraper, TicketInfo, TicketStatus
from core.logger import get_logger

logger = get_logger(__name__)

_STATUS_MAP = {
    "onsale": TicketStatus.AVAILABLE,
    "soldout": TicketStatus.SOLD_OUT,
    "coming_soon": TicketStatus.COMING_SOON,
}


class TicketPlusScraper(BaseScraper):
    platform = "ticket_plus"

    async def fetch(self, url: str) -> TicketInfo | None:
        try:
            html = await self._get_text(url)
        except Exception as exc:
            logger.error("ticket_plus_fetch_failed", url=url, error=str(exc))
            raise

        return self._parse(html, url)

    def _parse(self, html: str, url: str) -> TicketInfo:
        soup = BeautifulSoup(html, "lxml")

        name_tag = soup.select_one(".event-name, h1.title")
        name = name_tag.get_text(strip=True) if name_tag else ""

        venue_tag = soup.select_one(".venue, .location")
        venue = venue_tag.get_text(strip=True) if venue_tag else ""

        # Date
        date_tag = soup.select_one(".event-date, .show-date")
        event_date: datetime | None = None
        if date_tag:
            date_text = re.sub(r"\s+", " ", date_tag.get_text(strip=True))
            for fmt in ("%Y/%m/%d", "%Y.%m.%d", "%Y-%m-%d"):
                try:
                    event_date = datetime.strptime(date_text[:10], fmt)
                    break
                except ValueError:
                    pass

        # Status field — Ticket Plus often embeds it in data attributes
        status = TicketStatus.UNKNOWN
        status_tag = soup.select_one("[data-status], .ticket-status")
        if status_tag:
            raw = (status_tag.get("data-status") or status_tag.get_text(strip=True)).lower()
            status = _STATUS_MAP.get(raw, TicketStatus.UNKNOWN)

        # Seat types
        seat_tags = soup.select(".area-item .area-name, .ticket-zone")
        seat_types = [t.get_text(strip=True) for t in seat_tags if t.get_text(strip=True)]

        # Prices
        price_tags = soup.select(".price-value, .ticket-price")
        prices: list[float] = []
        for tag in price_tags:
            digits = re.sub(r"[^\d]", "", tag.get_text())
            if digits:
                prices.append(float(digits))
        price_range = {"min": min(prices), "max": max(prices)} if prices else {}

        id_match = re.search(r"/event/(\d+)", url)
        concert_id = id_match.group(1) if id_match else url

        return TicketInfo(
            platform=self.platform,
            concert_id=concert_id,
            name=name,
            artist="",
            venue=venue,
            date=event_date,
            ticket_url=url,
            seat_types=seat_types,
            price_range=price_range,
            status=status,
        )
