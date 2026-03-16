"""Unit tests for scraper parsers — no network calls required."""
from __future__ import annotations

import pytest

from scraper.base import TicketStatus
from scraper.kktix import KKTIXScraper
from scraper.tixcraft import TixCraftScraper
from scraper.kham import KhamScraper


# ──────────────────────────────────────────────
# KKTIX
# ──────────────────────────────────────────────

@pytest.fixture
def kktix_scraper():
    return KKTIXScraper()


def test_kktix_parse_available(kktix_scraper):
    data = {
        "id": 9999,
        "name": "Test Concert",
        "organizer": {"name": "Test Artist"},
        "venue": {"name": "Taipei Arena"},
        "start_at": "2026-06-01T18:00:00Z",
        "registration": {"status": "started"},
        "tickets": [
            {"name": "A區", "price": 1800},
            {"name": "B區", "price": 1200},
        ],
    }
    info = kktix_scraper._parse(data, "https://kktix.com/events/test")
    assert info.status == TicketStatus.AVAILABLE
    assert info.name == "Test Concert"
    assert info.price_range == {"min": 1200, "max": 1800}
    assert "A區" in info.seat_types


def test_kktix_parse_sold_out(kktix_scraper):
    data = {
        "id": 1234,
        "name": "Sold Out Show",
        "organizer": {"name": "Artist"},
        "venue": {"name": "Venue"},
        "registration": {"status": "ended"},
        "tickets": [],
    }
    info = kktix_scraper._parse(data, "https://kktix.com/events/soldout")
    assert info.status == TicketStatus.SOLD_OUT


def test_kktix_parse_coming_soon(kktix_scraper):
    data = {
        "id": 5678,
        "name": "Upcoming Show",
        "organizer": {"name": "Artist"},
        "venue": {"name": "Venue"},
        "registration": {"status": "not_started"},
        "tickets": [],
    }
    info = kktix_scraper._parse(data, "https://kktix.com/events/upcoming")
    assert info.status == TicketStatus.COMING_SOON


# ──────────────────────────────────────────────
# TixCraft
# ──────────────────────────────────────────────

@pytest.fixture
def tixcraft_scraper():
    return TixCraftScraper()


def test_tixcraft_parse_available(tixcraft_scraper):
    html = """
    <html>
      <body>
        <h1 class="activity-name">Big Concert</h1>
        <span class="activity-date">2026/07/15</span>
        <span class="activity-venue">National Stadium</span>
        <div class="btn-ticket">售票中</div>
        <div class="ticket-type-name">VIP區</div>
        <div class="ticket-price">NT$3,000</div>
      </body>
    </html>
    """
    info = tixcraft_scraper._parse(html, "https://tixcraft.com/activity/12345")
    assert info.status == TicketStatus.AVAILABLE
    assert info.name == "Big Concert"
    assert info.concert_id == "12345"


# ──────────────────────────────────────────────
# Base — content hash deduplication
# ──────────────────────────────────────────────

def test_content_hash_changes_on_status_change(kktix_scraper):
    data_available = {
        "id": 1, "name": "X", "organizer": {"name": "Y"}, "venue": {"name": "Z"},
        "registration": {"status": "started"},
        "tickets": [{"name": "A", "price": 1000}],
    }
    data_sold_out = {
        "id": 1, "name": "X", "organizer": {"name": "Y"}, "venue": {"name": "Z"},
        "registration": {"status": "ended"},
        "tickets": [{"name": "A", "price": 1000}],
    }
    info_a = kktix_scraper._parse(data_available, "https://kktix.com/events/x")
    info_b = kktix_scraper._parse(data_sold_out, "https://kktix.com/events/x")
    assert info_a.content_hash() != info_b.content_hash()


def test_content_hash_stable_when_no_change(kktix_scraper):
    data = {
        "id": 1, "name": "X", "organizer": {"name": "Y"}, "venue": {"name": "Z"},
        "registration": {"status": "started"},
        "tickets": [{"name": "A", "price": 1000}],
    }
    info_1 = kktix_scraper._parse(data, "https://kktix.com/events/x")
    info_2 = kktix_scraper._parse(data, "https://kktix.com/events/x")
    assert info_1.content_hash() == info_2.content_hash()
