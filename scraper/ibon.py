"""ibon (7-ELEVEN) scraper — Mixed SSR + JS; may require POST for seat availability."""
from __future__ import annotations

import re
from datetime import datetime

from bs4 import BeautifulSoup

from scraper.base import BaseScraper, TicketInfo, TicketStatus
from core.logger import get_logger

logger = get_logger(__name__)


class IbonScraper(BaseScraper):
    platform = "ibon"

    async def fetch(self, url: str) -> TicketInfo | None:
        try:
            html = await self._get_text(url)
        except Exception as exc:
            logger.error("ibon_fetch_failed", url=url, error=str(exc))
            raise

        return self._parse(html, url)

    def _parse(self, html: str, url: str) -> TicketInfo:
        soup = BeautifulSoup(html, "lxml")

        name_tag = soup.select_one(".activityName, h1.name")
        name = name_tag.get_text(strip=True) if name_tag else ""

        venue_tag = soup.select_one(".venueName, .venue")
        venue = venue_tag.get_text(strip=True) if venue_tag else ""

        # Date
        date_tag = soup.select_one(".showDate, .date")
        event_date: datetime | None = None
        if date_tag:
            date_text = date_tag.get_text(strip=True)
            for fmt in ("%Y/%m/%d", "%Y-%m-%d"):
                try:
                    event_date = datetime.strptime(date_text[:10], fmt)
                    break
                except ValueError:
                    pass

        # Status
        status = TicketStatus.UNKNOWN
        btn = soup.select_one(".buyTicketBtn, .ticket-btn")
        if btn:
            text = btn.get_text(strip=True)
            if "購票" in text or "買票" in text:
                status = TicketStatus.AVAILABLE
            elif "售完" in text or "完售" in text:
                status = TicketStatus.SOLD_OUT
            elif "即將" in text:
                status = TicketStatus.COMING_SOON

        # Seat types
        area_tags = soup.select(".areaName, .seatArea")
        seat_types = [t.get_text(strip=True) for t in area_tags if t.get_text(strip=True)]

        # Prices
        price_tags = soup.select(".priceValue, .ticketPrice")
        prices: list[float] = []
        for tag in price_tags:
            digits = re.sub(r"[^\d]", "", tag.get_text())
            if digits:
                prices.append(float(digits))
        price_range = {"min": min(prices), "max": max(prices)} if prices else {}

        id_match = re.search(r"actId=(\w+)", url)
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
