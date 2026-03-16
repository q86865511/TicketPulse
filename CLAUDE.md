# TicketPulse — Claude Project Guide

> Feel every drop before it's gone.
> A real-time concert ticket monitor that tracks releases, fires instant alerts, and logs your concert history — all in one place.

---

## Project Overview

**TicketPulse** is a Python-based concert ticket tracking system.

### Architecture Principles

- **Web App is the primary interface** — all user-facing features (watchlist, history, profile, settings) are built as web pages with HTML + JavaScript
- **Discord Bot is a notification channel** — after linking a Discord account, users receive real-time alerts and can run simple lookup commands; complex operations redirect users to the web app
- **Email is a secondary notification channel** — optional alongside Discord notifications

```
User Experience Flow:
  Web App (primary) ──────► All features: login, watchlist, history, profile, settings
  Discord Bot (secondary) ► Receive alerts + simple commands (/status, /watchlist, /link)
  Email (secondary) ──────► Ticket drop alerts only
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| Web Framework | FastAPI |
| Frontend | Jinja2 templates + Vanilla JS (fetch API) |
| Discord Bot | `discord.py` (v2.x) — gateway for alerts |
| Discord Interactions | FastAPI `/interactions` endpoint — HTTP slash commands |
| Database | PostgreSQL (via SQLAlchemy async ORM) |
| Task Queue / Scheduler | APScheduler |
| Notifications | Discord DM / Email (SMTP or SendGrid) |
| Auth (Web) | OAuth2 (Discord login) |
| Deployment | Docker + (Railway / Render / VPS) |

---

## Core Features

### 1. 🌐 Web App (Primary Interface)
- Discord OAuth2 login
- Dashboard: watchlist overview, recent alerts, history summary
- Watchlist management: add by URL, view status, remove
- Concert history: log attended/missed concerts, add notes
- Profile page: public/friends/private visibility
- Friends: send/accept requests, view friend profiles
- Settings: notification method, quiet hours, privacy

### 2. 🔔 Real-Time Ticket Drop Alerts
- Monitor KKTIX, TixCraft, Ticket Plus, ibon, 寬宏藝術 Kham
- Poll at configurable intervals with jitter
- Push notifications via:
  - Discord DM (via gateway bot)
  - Email (SMTP or SendGrid)
- Alert payload: concert name, venue, date, ticket URL, seat types, price range

### 3. 🤖 Discord Bot (Notification + Simple Commands)
- Sends ticket drop alerts as rich embeds via DM
- Simple slash commands (HTTP Interactions endpoint):
  - `/status` — check TicketPulse connection status
  - `/watchlist` — view current watchlist (summary, links to web app)
  - `/link` — get the web app link to manage full settings
  - `/alert-test` — send a test notification (admin)
- Complex operations (add/remove watchlist, change settings) redirect to Web App

### 4. 👤 User Account & Preferences
- Single account linked via Discord OAuth2
- Notification method: Discord DM / Email / Both
- Quiet hours (no alerts during configured time range)
- Profile visibility: public / friends-only / private
- Stored in DB, accessible via both Web App and Discord Bot

### 5. 👥 Friend Profiles & Social Features
- View other users' public concert history and watchlists
- Friend system: send/accept requests via Web App
- Privacy controls per user

---

## Project Structure

```
ticketpulse/
├── bot/                        # Discord Bot (gateway — for sending alerts)
│   ├── main.py                 # Bot entry point
│   ├── cogs/
│   │   ├── alerts.py           # Alert channel management (admin)
│   │   └── notifications.py    # Outbound notification sending
│   └── utils/
│       ├── embeds.py           # Discord embed templates
│       └── checks.py           # Permission / role checks
│
├── web/                        # Web App (FastAPI — primary user interface)
│   ├── main.py                 # FastAPI entry point
│   ├── routers/
│   │   ├── auth.py             # OAuth2 Discord login
│   │   ├── interactions.py     # Discord HTTP Interactions endpoint (/interactions)
│   │   ├── profile.py          # Profile & friends endpoints
│   │   ├── history.py          # Concert history endpoints
│   │   └── watchlist.py        # Watchlist endpoints
│   ├── templates/              # Jinja2 HTML templates
│   │   ├── base.html           # Base layout
│   │   ├── index.html          # Landing / dashboard
│   │   ├── watchlist.html      # Watchlist page
│   │   ├── history.html        # Concert history page
│   │   └── profile.html        # User profile page
│   └── static/
│       ├── css/style.css       # Main stylesheet
│       └── js/app.js           # Frontend JS (fetch API)
│
├── scraper/                    # Ticket monitoring engine
│   ├── base.py                 # Abstract scraper class + TicketInfo dataclass
│   ├── kktix.py
│   ├── tixcraft.py
│   ├── ticket_plus.py
│   ├── ibon.py
│   ├── kham.py
│   └── scheduler.py            # APScheduler job definitions
│
├── db/
│   ├── models.py               # SQLAlchemy ORM models
│   ├── crud.py                 # All DB operations (single entry point)
│   └── session.py              # Async session management
│
├── core/
│   ├── config.py               # pydantic-settings (all env vars)
│   ├── notifier.py             # Notification dispatcher (Discord + Email)
│   └── logger.py               # Structured logging
│
├── tests/
├── .env.example
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── CLAUDE.md
```

---

## Discord Bot Details

| Field | Value |
|---|---|
| Bot ID | `1483021120881033279` |
| Public Key | `7ecd745ac9ae4b6f6dd475f82855caed69e88ba1aafc72e36dd066cfc013dca2` |
| Interactions Endpoint URL | `https://<your-domain>/interactions` |

The `/interactions` endpoint must be registered in the Discord Developer Portal under:
**General Information → Interactions Endpoint URL**

The endpoint verifies every request using Ed25519 signature with the bot's Public Key.

---

## Database Models (Overview)

```
User
  - id, discord_id, username, avatar_url, email
  - notification_preference (discord_dm / email / both), quiet_hours_start, quiet_hours_end
  - profile_visibility (public / friends / private)
  - created_at

Concert
  - id, name, artist, venue, city, date
  - ticket_url, platform (kktix / tixcraft / ticket_plus / ibon / kham)
  - seat_types (JSON), min_price, max_price, sale_start_at
  - created_at

WatchlistItem
  - id, user_id → User, concert_id → Concert
  - status (watching / notified / expired)
  - added_at

ConcertHistory
  - id, user_id → User, concert_id → Concert
  - status (attended / missed / tracking)
  - notes, logged_at

Friendship
  - id, requester_id → User, receiver_id → User
  - status (pending / accepted / blocked)
  - created_at

AlertLog
  - id, concert_id → Concert, triggered_at
  - alert_type (first_drop / restock / ending_soon)
  - notified_user_count

ScraperState
  - id, platform, concert_id → Concert
  - last_seen_hash, last_checked_at
  - consecutive_failures, is_active
```

---

## Discord Bot Slash Commands (HTTP Interactions)

| Command | Description |
|---|---|
| `/status` | Check if your account is linked to TicketPulse |
| `/watchlist` | View a summary of your watchlist (link to web app for management) |
| `/link` | Get the web app URL to manage settings and watchlist |
| `/alert-test` | Send a test notification (admin only) |

> All complex operations (add/remove watchlist, edit settings, history) are handled by the Web App.
> The bot redirects users with a link when they try complex actions via Discord.

---

## Environment Variables

```env
# Discord
DISCORD_BOT_TOKEN=
DISCORD_CLIENT_ID=1483021120881033279
DISCORD_CLIENT_SECRET=
DISCORD_PUBLIC_KEY=7ecd745ac9ae4b6f6dd475f82855caed69e88ba1aafc72e36dd066cfc013dca2
DISCORD_REDIRECT_URI=http://localhost:8000/auth/callback

# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/ticketpulse

# Redis
REDIS_URL=redis://localhost:6379

# Email — SMTP
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USERNAME=
EMAIL_PASSWORD=
EMAIL_FROM=TicketPulse <no-reply@ticketpulse.app>

# Email — SendGrid (leave blank to use SMTP)
SENDGRID_API_KEY=

# App
APP_SECRET_KEY=change-me-to-a-random-secret
APP_BASE_URL=http://localhost:8000
DEBUG=false
SCRAPER_INTERVAL_SECONDS=60
```

---

## Target Ticket Platforms

| Platform | Domain | Notes |
|---|---|---|
| **KKTIX** | kktix.com | REST JSON API; primary TW indie/pop target |
| **TixCraft** | tixcraft.com | HTML-heavy + Cloudflare; session management needed |
| **Ticket Plus** (拓元) | ticket.com.tw | AJAX-driven; parse `onsale/soldout/coming_soon` status |
| **ibon** (7-ELEVEN) | ibon.7-eleven.com.tw | Mixed SSR+JS; may require POST for seat availability |
| **寬宏藝術 Kham** | kham.com.tw | Simple HTML; monitor event listing + detail pages |

---

## Scraper Strategy

### Deduplication
- Store SHA-256 hash of relevant content in `ScraperState.last_seen_hash`
- Only trigger alert if hash changes AND status is now `available`
- Never re-alert same `(concert_id, alert_type)` unless status resets

### Rate Limiting & Anti-Bot
- Configurable per-platform intervals; default `SCRAPER_INTERVAL_SECONDS`
- Randomized jitter ±10–30% on every poll
- Exponential backoff on 429/503
- Circuit-breaker after `N` consecutive failures

### Data Normalization
- All scrapers return `TicketInfo` (defined in `scraper/base.py`)
- Status: `available / sold_out / coming_soon / unknown`

---

## Development Guidelines

- **Web App is primary** — all features must work fully via the web interface
- **Discord Bot is secondary** — only outbound notifications and simple read-only commands
- Always use **async/await** — FastAPI and discord.py are both async-first
- All DB operations go through `db/crud.py` — no raw queries in routes or cogs
- Scraper classes must extend `scraper/base.py`
- Use `pydantic-settings` for all config — never hardcode secrets or URLs
- Use structured logging via `core/logger.py`, never plain `print()`
- The `/interactions` endpoint must verify Ed25519 signatures before processing any command

---

## Out of Scope (for now)

- Automated ticket purchasing / checkout automation
- Payment processing
- Mobile app

---

## Notes for Claude

- Web App (`web/`) is the primary user interface — prioritize web features over bot features
- Discord Bot (`bot/`) only sends notifications and handles simple read-only slash commands
- The `/interactions` endpoint in `web/routers/interactions.py` handles all Discord slash commands via HTTP; always verify the signature using `DISCORD_PUBLIC_KEY` before processing
- When adding new scrapers, always follow the pattern in `scraper/base.py`
- Always check `core/config.py` before adding new environment variables
- The Web App and Discord Bot share the same database — keep models in sync
- Friendship is bidirectional — always query both directions when checking friendship status
- New web pages go in `web/templates/` with corresponding JS in `web/static/js/`
