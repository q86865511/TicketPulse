"""寬宏藝術 (Kham) scraper — straightforward HTML structure."""
from __future__ import annotations

import re
from datetime import datetime

from bs4 import BeautifulSoup

from scraper.base import BaseScraper, TicketInfo, TicketStatus
from core.logger import get_logger

logger = get_logger(__name__)


class KhamScraper(BaseScraper):
    platform = "kham"

    async def fetch(self, url: str) -> TicketInfo | None:
        try:
            html = await self._get_text(url)
        except Exception as exc:
            logger.error("kham_fetch_failed", url=url, error=str(exc))
            raise

        return self._parse(html, url)

    def _parse(self, html: str, url: str) -> TicketInfo:
        soup = BeautifulSoup(html, "lxml")

        name_tag = soup.select_one(".show-title h1, .title h1, h1")
        name = name_tag.get_text(strip=True) if name_tag else ""

        venue_tag = soup.select_one(".show-venue, .venue")
        venue = venue_tag.get_text(strip=True) if venue_tag else ""

        # Date — Kham often has a readable date block
        date_tag = soup.select_one(".show-date, .date")
        event_date: datetime | None = None
        if date_tag:
            date_text = date_tag.get_text(strip=True)
            for fmt in ("%Y/%m/%d", "%Y.%m.%d", "%Y-%m-%d"):
                try:
                    event_date = datetime.strptime(date_text[:10], fmt)
                    break
                except ValueError:
                    pass

        # Status
        status = TicketStatus.UNKNOWN
        buy_btn = soup.select_one("a.buy-btn, .ticket-link")
        if buy_btn:
            href = buy_btn.get("href", "")
            text = buy_btn.get_text(strip=True)
            if href and "javascript" not in href.lower():
                status = TicketStatus.AVAILABLE
            elif "售完" in text or "完售" in text:
                status = TicketStatus.SOLD_OUT

        sold_out_tag = soup.select_one(".sold-out, .soldout")
        if sold_out_tag:
            status = TicketStatus.SOLD_OUT

        # Seat types
        area_tags = soup.select(".area-item, .seat-area")
        seat_types = [t.get_text(strip=True) for t in area_tags if t.get_text(strip=True)]

        # Prices
        price_tags = soup.select(".price, .ticket-price")
        prices: list[float] = []
        for tag in price_tags:
            digits = re.sub(r"[^\d]", "", tag.get_text())
            if digits:
                prices.append(float(digits))
        price_range = {"min": min(prices), "max": max(prices)} if prices else {}

        id_match = re.search(r"/show/(\d+)", url)
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
