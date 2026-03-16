"""
All database operations must go through this module.
Route handlers and Discord cogs must NOT write raw queries.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import (
    AlertLog,
    AlertType,
    Concert,
    ConcertHistory,
    ConcertHistoryStatus,
    Friendship,
    FriendshipStatus,
    NotificationPreference,
    ProfileVisibility,
    ScraperState,
    TicketPlatform,
    User,
    WatchlistItem,
    WatchlistStatus,
)


# ──────────────────────────────────────────────
# User
# ──────────────────────────────────────────────

async def get_user_by_discord_id(db: AsyncSession, discord_id: str) -> User | None:
    result = await db.execute(select(User).where(User.discord_id == discord_id))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    discord_id: str,
    username: str,
    avatar_url: str | None = None,
    email: str | None = None,
) -> User:
    user = User(discord_id=discord_id, username=username, avatar_url=avatar_url, email=email)
    db.add(user)
    await db.flush()
    return user


async def update_user_preferences(
    db: AsyncSession,
    user_id: int,
    notification_preference: NotificationPreference | None = None,
    quiet_hours_start: int | None = None,
    quiet_hours_end: int | None = None,
    profile_visibility: ProfileVisibility | None = None,
    email: str | None = None,
) -> User | None:
    user = await get_user_by_id(db, user_id)
    if not user:
        return None
    if notification_preference is not None:
        user.notification_preference = notification_preference
    if quiet_hours_start is not None:
        user.quiet_hours_start = quiet_hours_start
    if quiet_hours_end is not None:
        user.quiet_hours_end = quiet_hours_end
    if profile_visibility is not None:
        user.profile_visibility = profile_visibility
    if email is not None:
        user.email = email
    await db.flush()
    return user


# ──────────────────────────────────────────────
# Concert
# ──────────────────────────────────────────────

async def get_concert_by_id(db: AsyncSession, concert_id: int) -> Concert | None:
    result = await db.execute(select(Concert).where(Concert.id == concert_id))
    return result.scalar_one_or_none()


async def search_concerts(db: AsyncSession, query: str) -> list[Concert]:
    pattern = f"%{query}%"
    result = await db.execute(
        select(Concert).where(
            or_(Concert.name.ilike(pattern), Concert.artist.ilike(pattern))
        )
    )
    return list(result.scalars().all())


async def create_concert(
    db: AsyncSession,
    name: str,
    artist: str,
    venue: str,
    city: str,
    ticket_url: str,
    platform: TicketPlatform,
    date: datetime | None = None,
    seat_types: list | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    sale_start_at: datetime | None = None,
) -> Concert:
    concert = Concert(
        name=name,
        artist=artist,
        venue=venue,
        city=city,
        ticket_url=ticket_url,
        platform=platform,
        date=date,
        seat_types=seat_types or [],
        min_price=min_price,
        max_price=max_price,
        sale_start_at=sale_start_at,
    )
    db.add(concert)
    await db.flush()
    return concert


# ──────────────────────────────────────────────
# Watchlist
# ──────────────────────────────────────────────

async def add_to_watchlist(db: AsyncSession, user_id: int, concert_id: int) -> WatchlistItem:
    item = WatchlistItem(user_id=user_id, concert_id=concert_id)
    db.add(item)
    await db.flush()
    return item


async def get_watchlist(db: AsyncSession, user_id: int) -> list[WatchlistItem]:
    result = await db.execute(
        select(WatchlistItem).where(WatchlistItem.user_id == user_id)
    )
    return list(result.scalars().all())


async def remove_from_watchlist(db: AsyncSession, user_id: int, item_id: int) -> bool:
    result = await db.execute(
        select(WatchlistItem).where(
            and_(WatchlistItem.id == item_id, WatchlistItem.user_id == user_id)
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        return False
    await db.delete(item)
    await db.flush()
    return True


async def get_watchlist_item(db: AsyncSession, user_id: int, concert_id: int) -> WatchlistItem | None:
    result = await db.execute(
        select(WatchlistItem).where(
            and_(WatchlistItem.user_id == user_id, WatchlistItem.concert_id == concert_id)
        )
    )
    return result.scalar_one_or_none()


async def get_watching_users_for_concert(db: AsyncSession, concert_id: int) -> list[User]:
    """Return all users actively watching a concert (for alert dispatch)."""
    result = await db.execute(
        select(User)
        .join(WatchlistItem, WatchlistItem.user_id == User.id)
        .where(
            and_(
                WatchlistItem.concert_id == concert_id,
                WatchlistItem.status == WatchlistStatus.WATCHING,
            )
        )
    )
    return list(result.scalars().all())


# ──────────────────────────────────────────────
# Concert History
# ──────────────────────────────────────────────

async def add_concert_history(
    db: AsyncSession,
    user_id: int,
    concert_id: int,
    status: ConcertHistoryStatus = ConcertHistoryStatus.ATTENDED,
    notes: str | None = None,
) -> ConcertHistory:
    entry = ConcertHistory(user_id=user_id, concert_id=concert_id, status=status, notes=notes)
    db.add(entry)
    await db.flush()
    return entry


async def get_concert_history(db: AsyncSession, user_id: int) -> list[ConcertHistory]:
    result = await db.execute(
        select(ConcertHistory).where(ConcertHistory.user_id == user_id)
    )
    return list(result.scalars().all())


# ──────────────────────────────────────────────
# Friendship
# ──────────────────────────────────────────────

async def get_friendship(
    db: AsyncSession, user_a_id: int, user_b_id: int
) -> Friendship | None:
    """Bidirectional lookup — order of arguments does not matter."""
    result = await db.execute(
        select(Friendship).where(
            or_(
                and_(Friendship.requester_id == user_a_id, Friendship.receiver_id == user_b_id),
                and_(Friendship.requester_id == user_b_id, Friendship.receiver_id == user_a_id),
            )
        )
    )
    return result.scalar_one_or_none()


async def send_friend_request(
    db: AsyncSession, requester_id: int, receiver_id: int
) -> Friendship | None:
    existing = await get_friendship(db, requester_id, receiver_id)
    if existing:
        return None  # Already exists
    friendship = Friendship(requester_id=requester_id, receiver_id=receiver_id)
    db.add(friendship)
    await db.flush()
    return friendship


async def accept_friend_request(
    db: AsyncSession, friendship_id: int, receiver_id: int
) -> Friendship | None:
    result = await db.execute(
        select(Friendship).where(
            and_(Friendship.id == friendship_id, Friendship.receiver_id == receiver_id)
        )
    )
    friendship = result.scalar_one_or_none()
    if not friendship:
        return None
    friendship.status = FriendshipStatus.ACCEPTED
    await db.flush()
    return friendship


async def get_friends(db: AsyncSession, user_id: int) -> list[User]:
    """Return all accepted friends of a user."""
    result = await db.execute(
        select(User).where(
            or_(
                and_(
                    Friendship.requester_id == user_id,
                    Friendship.status == FriendshipStatus.ACCEPTED,
                    User.id == Friendship.receiver_id,
                ),
                and_(
                    Friendship.receiver_id == user_id,
                    Friendship.status == FriendshipStatus.ACCEPTED,
                    User.id == Friendship.requester_id,
                ),
            )
        ).join(
            Friendship,
            or_(Friendship.requester_id == user_id, Friendship.receiver_id == user_id),
        )
    )
    return list(result.scalars().unique().all())


# ──────────────────────────────────────────────
# AlertLog
# ──────────────────────────────────────────────

async def create_alert_log(
    db: AsyncSession,
    concert_id: int,
    alert_type: AlertType,
    notified_user_count: int,
) -> AlertLog:
    log = AlertLog(
        concert_id=concert_id,
        alert_type=alert_type,
        notified_user_count=notified_user_count,
    )
    db.add(log)
    await db.flush()
    return log


async def has_recent_alert(
    db: AsyncSession, concert_id: int, alert_type: AlertType
) -> bool:
    """Prevent duplicate alerts for the same (concert, alert_type) pair."""
    result = await db.execute(
        select(AlertLog).where(
            and_(AlertLog.concert_id == concert_id, AlertLog.alert_type == alert_type)
        )
    )
    return result.scalar_one_or_none() is not None


# ──────────────────────────────────────────────
# ScraperState
# ──────────────────────────────────────────────

async def get_scraper_state(db: AsyncSession, concert_id: int) -> ScraperState | None:
    result = await db.execute(
        select(ScraperState).where(ScraperState.concert_id == concert_id)
    )
    return result.scalar_one_or_none()


async def upsert_scraper_state(
    db: AsyncSession,
    platform: TicketPlatform,
    concert_id: int,
    last_seen_hash: str | None,
    last_checked_at: datetime,
    consecutive_failures: int = 0,
) -> ScraperState:
    state = await get_scraper_state(db, concert_id)
    if state:
        state.last_seen_hash = last_seen_hash
        state.last_checked_at = last_checked_at
        state.consecutive_failures = consecutive_failures
    else:
        state = ScraperState(
            platform=platform,
            concert_id=concert_id,
            last_seen_hash=last_seen_hash,
            last_checked_at=last_checked_at,
            consecutive_failures=consecutive_failures,
        )
        db.add(state)
    await db.flush()
    return state


async def get_active_scraper_states(db: AsyncSession) -> list[ScraperState]:
    result = await db.execute(
        select(ScraperState).where(ScraperState.is_active.is_(True))
    )
    return list(result.scalars().all())
