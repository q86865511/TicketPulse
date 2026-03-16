"""TixCraft scraper — HTML parsing with session cookie management."""
from __future__ import annotations

import re
from datetime import datetime

from bs4 import BeautifulSoup

from scraper.base import BaseScraper, TicketInfo, TicketStatus
from core.logger import get_logger

logger = get_logger(__name__)


class TixCraftScraper(BaseScraper):
    platform = "tixcraft"

    async def fetch(self, url: str) -> TicketInfo | None:
        try:
            html = await self._get_text(url)
        except Exception as exc:
            logger.error("tixcraft_fetch_failed", url=url, error=str(exc))
            raise

        return self._parse(html, url)

    def _parse(self, html: str, url: str) -> TicketInfo:
        soup = BeautifulSoup(html, "lxml")

        # Event name
        name_tag = soup.select_one("h1.activity-name, .event-title h1")
        name = name_tag.get_text(strip=True) if name_tag else ""

        # Date
        date_tag = soup.select_one("span.activity-date, .event-date")
        event_date: datetime | None = None
        if date_tag:
            date_text = date_tag.get_text(strip=True)
            for fmt in ("%Y/%m/%d", "%Y-%m-%d"):
                try:
                    event_date = datetime.strptime(date_text[:10], fmt)
                    break
                except ValueError:
                    pass

        # Venue
        venue_tag = soup.select_one(".activity-venue, .venue-name")
        venue = venue_tag.get_text(strip=True) if venue_tag else ""

        # Ticket status — look for common status indicators
        status = TicketStatus.UNKNOWN
        status_tag = soup.select_one(".ticket-status, .btn-ticket")
        if status_tag:
            text = status_tag.get_text(strip=True).lower()
            if "售票中" in text or "onsale" in text or "buy" in text:
                status = TicketStatus.AVAILABLE
            elif "售完" in text or "soldout" in text or "sold out" in text:
                status = TicketStatus.SOLD_OUT
            elif "即將" in text or "coming" in text:
                status = TicketStatus.COMING_SOON

        # Seat types
        seat_tags = soup.select(".ticket-type-name, .area-name")
        seat_types = [t.get_text(strip=True) for t in seat_tags if t.get_text(strip=True)]

        # Price range
        price_tags = soup.select(".ticket-price, .price")
        prices: list[float] = []
        for tag in price_tags:
            text = re.sub(r"[^\d]", "", tag.get_text())
            if text:
                prices.append(float(text))
        price_range = {"min": min(prices), "max": max(prices)} if prices else {}

        # External concert ID from URL
        id_match = re.search(r"/activity/(\d+)", url)
        concert_id = id_match.group(1) if id_match else url

        return TicketInfo(
            platform=self.platform,
            concert_id=concert_id,
            name=name,
            artist="",  # TixCraft doesn't always expose a dedicated artist field
            venue=venue,
            date=event_date,
            ticket_url=url,
            seat_types=seat_types,
            price_range=price_range,
            status=status,
        )
