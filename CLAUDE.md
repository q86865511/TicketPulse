# TicketPulse — Claude Project Guide

> Feel every drop before it's gone.
> A real-time concert ticket monitor that tracks releases, fires instant alerts, and logs your concert history — all in one place.

---

## Project Overview

**TicketPulse** is a Python-based concert ticket tracking system with two interfaces:
- A **Discord Bot** for real-time alerts and social features
- A **Web App** for browsing concert history, managing preferences, and viewing friend profiles

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| Discord Bot | `discord.py` (v2.x) |
| Web Framework | FastAPI (or Flask — TBD) |
| Database | PostgreSQL (via SQLAlchemy ORM) |
| Task Queue / Scheduler | APScheduler or Celery + Redis |
| Notifications | Discord webhooks / DM |
| Auth (Web) | OAuth2 (Discord login) |
| Deployment | Docker + (Railway / Render / VPS) |

---

## Core Features

### 1. 🔔 Real-Time Ticket Drop Alerts
- Monitor ticket platforms (e.g., KKTIX, Tixcraft, ibon) for new releases or restocks
- Scrape / poll target URLs at a configurable interval
- Immediately push a Discord DM or channel notification when tickets become available
- Include: concert name, venue, date, ticket link, seat types, and price

### 2. 🎯 Watchlist & Concert Reminders
- Users can add concerts they want to track (`/watch add <concert>`)
- Support fuzzy search or URL-based tracking
- Notify users when:
  - Tickets go on sale (first drop)
  - Resale / additional tickets are released
  - Sale is ending soon
- Users can remove or list their watchlist (`/watch list`, `/watch remove`)

### 3. 📚 Concert History Storage
- Log every concert a user has attended or tracked
- Store: concert name, artist, date, venue, ticket status (attended / missed / watching)
- Users can manually add past concerts to their profile
- History is visible on their Web App profile page

### 4. 👤 User Account & Preferences
- Discord OAuth2 login for the Web App
- Per-user settings:
  - Notification method (DM / channel mention)
  - Alert frequency / quiet hours
  - Preferred artists or genres (future: smart recommendations)
  - Language preference
- Stored in the database, synced between Discord Bot and Web App

### 5. 👥 Friend Profiles & Social Features
- Users can view other users' public concert history and watchlists
- Friend system: send/accept friend requests via Discord or Web App
- Public profile page shows:
  - Attended concerts
  - Currently watching concerts
  - Favorite artists (optional, user-controlled)
- Privacy controls: users can set profile to public / friends-only / private

---

## Project Structure

```
ticketpulse/
├── bot/                        # Discord Bot
│   ├── main.py                 # Bot entry point
│   ├── cogs/
│   │   ├── alerts.py           # Ticket drop alert commands
│   │   ├── watchlist.py        # /watch commands
│   │   ├── history.py          # Concert history commands
│   │   ├── profile.py          # User profile & friends commands
│   │   └── settings.py         # User preferences commands
│   └── utils/
│       ├── embeds.py           # Discord embed templates
│       └── checks.py           # Permission / role checks
│
├── web/                        # Web App (FastAPI)
│   ├── main.py                 # FastAPI entry point
│   ├── routers/
│   │   ├── auth.py             # OAuth2 Discord login
│   │   ├── profile.py          # Profile & friends endpoints
│   │   ├── history.py          # Concert history endpoints
│   │   └── watchlist.py        # Watchlist endpoints
│   ├── templates/              # Jinja2 HTML templates (if SSR)
│   └── static/                 # CSS / JS assets
│
├── scraper/                    # Ticket monitoring engine
│   ├── base.py                 # Abstract scraper class
│   ├── kktix.py                # KKTIX scraper
│   ├── tixcraft.py             # Tixcraft scraper
│   └── scheduler.py            # APScheduler job definitions
│
├── db/                         # Database layer
│   ├── models.py               # SQLAlchemy models
│   ├── crud.py                 # CRUD operations
│   └── session.py              # DB session management
│
├── core/
│   ├── config.py               # Env vars & settings (pydantic-settings)
│   ├── notifier.py             # Notification dispatcher
│   └── logger.py               # Structured logging setup
│
├── tests/                      # Unit & integration tests
├── .env.example
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── claude.md                   # This file
```

---

## Database Models (Overview)

```
User
  - id, discord_id, username, avatar_url
  - notification_preference, quiet_hours_start, quiet_hours_end
  - profile_visibility (public / friends / private)
  - created_at

Concert
  - id, name, artist, venue, city, date
  - ticket_url, platform (kktix / tixcraft / etc.)
  - created_at

WatchlistItem
  - id, user_id → User, concert_id → Concert
  - status (watching / notified / expired)
  - added_at

ConcertHistory
  - id, user_id → User, concert_id → Concert
  - status (attended / missed / tracking)
  - notes (optional user note)
  - logged_at

Friendship
  - id, requester_id → User, receiver_id → User
  - status (pending / accepted / blocked)
  - created_at

AlertLog
  - id, concert_id → Concert, triggered_at
  - alert_type (first_drop / restock / ending_soon)
  - notified_user_count
```

---

## Key Commands (Discord Bot)

| Command | Description |
|---|---|
| `/watch add <url or name>` | Add a concert to your watchlist |
| `/watch list` | View your current watchlist |
| `/watch remove <id>` | Remove a concert from watchlist |
| `/history add <concert>` | Manually log a past concert |
| `/history view` | View your concert history |
| `/profile` | View your own profile |
| `/profile view @user` | View a friend's profile |
| `/friend add @user` | Send a friend request |
| `/friend list` | View your friends |
| `/settings notifications` | Configure alert preferences |
| `/settings privacy` | Set profile visibility |

---

## Environment Variables

```env
# Discord
DISCORD_BOT_TOKEN=
DISCORD_CLIENT_ID=
DISCORD_CLIENT_SECRET=
DISCORD_REDIRECT_URI=

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/ticketpulse

# Redis (for task queue)
REDIS_URL=redis://localhost:6379

# App
APP_SECRET_KEY=
DEBUG=false
SCRAPER_INTERVAL_SECONDS=60
```

---

## Development Guidelines

- Always use **async/await** patterns — both `discord.py` and `FastAPI` are async-first
- All database operations go through `db/crud.py` — never write raw queries in route handlers or cogs
- Scraper classes must extend `scraper/base.py` — do not write standalone scraper scripts
- Use **pydantic-settings** for all config — never hardcode secrets or URLs
- Write tests for all CRUD operations and scraper parsers
- Use structured logging via `core/logger.py`, never plain `print()`
- Follow the **cog pattern** strictly for Discord commands — one feature per cog file

---

## Out of Scope (for now)

- Automated ticket purchasing / checkout automation
- Payment processing
- Mobile app
- Email notifications (Discord-only for now)

---

## Notes for Claude

- When adding new scrapers, always follow the pattern in `scraper/base.py`
- When adding new Discord commands, place them in the correct cog under `bot/cogs/`
- Always check `core/config.py` before adding new environment variables
- The Web App and Discord Bot share the same database — keep models in sync
- Friendship is bidirectional — always query both directions when checking friendship status
