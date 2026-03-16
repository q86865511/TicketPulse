"""Integration tests for db/crud.py — requires a real PostgreSQL instance."""
from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from db.models import Base, FriendshipStatus
import db.crud as crud

TEST_DATABASE_URL = "postgresql+asyncpg://ticketpulse:ticketpulse@localhost:5432/ticketpulse_test"


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.asyncio
async def test_create_and_get_user(db_session):
    user = await crud.create_user(db_session, discord_id="123456789", username="TestUser")
    await db_session.flush()

    fetched = await crud.get_user_by_discord_id(db_session, "123456789")
    assert fetched is not None
    assert fetched.username == "TestUser"


@pytest.mark.asyncio
async def test_watchlist_add_remove(db_session):
    from db.models import TicketPlatform

    user = await crud.create_user(db_session, discord_id="111", username="WatchUser")
    concert = await crud.create_concert(
        db_session,
        name="Test Concert",
        artist="Test Artist",
        venue="Test Venue",
        city="Taipei",
        ticket_url="https://kktix.com/events/test",
        platform=TicketPlatform.KKTIX,
    )
    await db_session.flush()

    item = await crud.add_to_watchlist(db_session, user.id, concert.id)
    assert item.id is not None

    items = await crud.get_watchlist(db_session, user.id)
    assert len(items) == 1

    removed = await crud.remove_from_watchlist(db_session, user.id, item.id)
    assert removed is True

    items_after = await crud.get_watchlist(db_session, user.id)
    assert len(items_after) == 0


@pytest.mark.asyncio
async def test_friendship_bidirectional(db_session):
    user_a = await crud.create_user(db_session, discord_id="aaa", username="UserA")
    user_b = await crud.create_user(db_session, discord_id="bbb", username="UserB")
    await db_session.flush()

    friendship = await crud.send_friend_request(db_session, user_a.id, user_b.id)
    assert friendship is not None

    # Bidirectional lookup — both directions must return the same record
    found_ab = await crud.get_friendship(db_session, user_a.id, user_b.id)
    found_ba = await crud.get_friendship(db_session, user_b.id, user_a.id)
    assert found_ab is not None
    assert found_ba is not None
    assert found_ab.id == found_ba.id

    accepted = await crud.accept_friend_request(db_session, friendship.id, user_b.id)
    assert accepted is not None
    assert accepted.status == FriendshipStatus.ACCEPTED


@pytest.mark.asyncio
async def test_concert_history(db_session):
    from db.models import ConcertHistoryStatus, TicketPlatform

    user = await crud.create_user(db_session, discord_id="222", username="HistUser")
    concert = await crud.create_concert(
        db_session,
        name="Past Concert",
        artist="Old Artist",
        venue="Arena",
        city="Taipei",
        ticket_url="https://kktix.com/events/past",
        platform=TicketPlatform.KKTIX,
    )
    await db_session.flush()

    entry = await crud.add_concert_history(
        db_session, user.id, concert.id, ConcertHistoryStatus.ATTENDED, notes="Great show!"
    )
    assert entry.notes == "Great show!"

    history = await crud.get_concert_history(db_session, user.id)
    assert len(history) == 1
    assert history[0].status == ConcertHistoryStatus.ATTENDED
