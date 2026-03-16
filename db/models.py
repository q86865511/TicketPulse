"""SQLAlchemy ORM models for TicketPulse."""
from __future__ import annotations

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ──────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────

class ProfileVisibility(str, enum.Enum):
    PUBLIC = "public"
    FRIENDS = "friends"
    PRIVATE = "private"


class NotificationPreference(str, enum.Enum):
    DISCORD_DM = "discord_dm"
    DISCORD_CHANNEL = "discord_channel"
    EMAIL = "email"
    BOTH = "both"


class TicketPlatform(str, enum.Enum):
    KKTIX = "kktix"
    TIXCRAFT = "tixcraft"
    TICKET_PLUS = "ticket_plus"
    IBON = "ibon"
    KHAM = "kham"


class WatchlistStatus(str, enum.Enum):
    WATCHING = "watching"
    NOTIFIED = "notified"
    EXPIRED = "expired"


class ConcertHistoryStatus(str, enum.Enum):
    ATTENDED = "attended"
    MISSED = "missed"
    TRACKING = "tracking"


class FriendshipStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    BLOCKED = "blocked"


class AlertType(str, enum.Enum):
    FIRST_DROP = "first_drop"
    RESTOCK = "restock"
    ENDING_SOON = "ending_soon"


# ──────────────────────────────────────────────
# Models
# ──────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    discord_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True, index=True)
    notification_preference: Mapped[NotificationPreference] = mapped_column(
        Enum(NotificationPreference), default=NotificationPreference.DISCORD_DM, nullable=False
    )
    quiet_hours_start: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 0-23
    quiet_hours_end: Mapped[int | None] = mapped_column(Integer, nullable=True)    # 0-23
    profile_visibility: Mapped[ProfileVisibility] = mapped_column(
        Enum(ProfileVisibility), default=ProfileVisibility.PUBLIC, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    watchlist_items: Mapped[list[WatchlistItem]] = relationship("WatchlistItem", back_populates="user", lazy="selectin")
    concert_history: Mapped[list[ConcertHistory]] = relationship("ConcertHistory", back_populates="user", lazy="selectin")
    sent_requests: Mapped[list[Friendship]] = relationship(
        "Friendship", foreign_keys="Friendship.requester_id", back_populates="requester", lazy="selectin"
    )
    received_requests: Mapped[list[Friendship]] = relationship(
        "Friendship", foreign_keys="Friendship.receiver_id", back_populates="receiver", lazy="selectin"
    )


class Concert(Base):
    __tablename__ = "concerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    artist: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    venue: Mapped[str] = mapped_column(String(200), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ticket_url: Mapped[str] = mapped_column(Text, nullable=False)
    platform: Mapped[TicketPlatform] = mapped_column(Enum(TicketPlatform), nullable=False, index=True)
    seat_types: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    min_price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    max_price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    sale_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    watchlist_items: Mapped[list[WatchlistItem]] = relationship("WatchlistItem", back_populates="concert")
    history_entries: Mapped[list[ConcertHistory]] = relationship("ConcertHistory", back_populates="concert")
    scraper_state: Mapped[ScraperState | None] = relationship("ScraperState", back_populates="concert", uselist=False)
    alert_logs: Mapped[list[AlertLog]] = relationship("AlertLog", back_populates="concert")


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"
    __table_args__ = (UniqueConstraint("user_id", "concert_id", name="uq_watchlist_user_concert"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    concert_id: Mapped[int] = mapped_column(ForeignKey("concerts.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[WatchlistStatus] = mapped_column(
        Enum(WatchlistStatus), default=WatchlistStatus.WATCHING, nullable=False
    )
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship("User", back_populates="watchlist_items")
    concert: Mapped[Concert] = relationship("Concert", back_populates="watchlist_items")


class ConcertHistory(Base):
    __tablename__ = "concert_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    concert_id: Mapped[int] = mapped_column(ForeignKey("concerts.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[ConcertHistoryStatus] = mapped_column(
        Enum(ConcertHistoryStatus), default=ConcertHistoryStatus.TRACKING, nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship("User", back_populates="concert_history")
    concert: Mapped[Concert] = relationship("Concert", back_populates="history_entries")


class Friendship(Base):
    __tablename__ = "friendships"
    __table_args__ = (UniqueConstraint("requester_id", "receiver_id", name="uq_friendship_pair"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    requester_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    receiver_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[FriendshipStatus] = mapped_column(
        Enum(FriendshipStatus), default=FriendshipStatus.PENDING, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    requester: Mapped[User] = relationship("User", foreign_keys=[requester_id], back_populates="sent_requests")
    receiver: Mapped[User] = relationship("User", foreign_keys=[receiver_id], back_populates="received_requests")


class AlertLog(Base):
    __tablename__ = "alert_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    concert_id: Mapped[int] = mapped_column(ForeignKey("concerts.id", ondelete="CASCADE"), nullable=False)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    alert_type: Mapped[AlertType] = mapped_column(Enum(AlertType), nullable=False)
    notified_user_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    concert: Mapped[Concert] = relationship("Concert", back_populates="alert_logs")


class ScraperState(Base):
    __tablename__ = "scraper_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform: Mapped[TicketPlatform] = mapped_column(Enum(TicketPlatform), nullable=False, index=True)
    concert_id: Mapped[int] = mapped_column(
        ForeignKey("concerts.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    last_seen_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    concert: Mapped[Concert] = relationship("Concert", back_populates="scraper_state")
