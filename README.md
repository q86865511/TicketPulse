# 🎫 TicketPulse

> **Feel every drop before it's gone.**
> 即時演唱會票券監控系統 — 搶先掌握開賣時機，再也不錯過喜愛的演出。

---

## 目錄

- [專案簡介](#專案簡介)
- [功能特色](#功能特色)
- [支援平台](#支援平台)
- [技術架構](#技術架構)
- [首次啟動（從零開始）](#首次啟動從零開始)
  - [Step 1 — 確認環境](#step-1--確認環境)
  - [Step 2 — 取得 Discord 憑證](#step-2--取得-discord-憑證)
  - [Step 3 — 建立 .env 檔案](#step-3--建立-env-檔案)
  - [Step 4 — 設定 Discord OAuth2 Redirect URI](#step-4--設定-discord-oauth2-redirect-uri)
  - [Step 5 — 啟動所有服務](#step-5--啟動所有服務)
  - [Step 6 — 開啟網頁](#step-6--開啟網頁)
  - [Step 7 — 邀請 Bot 到 Discord 伺服器](#step-7--邀請-bot-到-discord-伺服器)
  - [Step 8 — 設定 Interactions Endpoint（選用）](#step-8--設定-interactions-endpoint選用)
- [Email 通知設定](#email-通知設定)
- [使用說明](#使用說明)
- [Discord Bot 指令](#discord-bot-指令)
- [專案結構](#專案結構)
- [開發指南](#開發指南)
- [常見問題](#常見問題)

---

## 專案簡介

TicketPulse 是一套以 **Python + FastAPI** 為核心的演唱會票券追蹤系統。

### 使用架構

```
使用者
  │
  ├─ 網頁（主要）────────► 登入 / 關注清單 / 歷史紀錄 / 個人資料 / 設定
  │
  ├─ Discord Bot（通知）─► 票券開賣即時推播 DM + 簡單查詢指令
  │
  └─ Email（通知）───────► 票券開賣通知信
```

- **網頁是主要操作介面**，所有功能均可在瀏覽器完成
- **Discord Bot** 負責即時推播通知，並提供幾個輕量查詢指令
- **Email** 為可選的補充通知管道

---

## 功能特色

| 功能 | 說明 |
|---|---|
| 🔔 即時票券通知 | 票券一開售，立即發送 Discord DM 或 Email |
| 🎯 關注清單 | 貼上售票網址，自動追蹤票券狀態 |
| 📚 演唱會歷史 | 記錄已參加、錯過、追蹤中的演唱會 |
| 👤 個人資料 | 可公開／限好友／私人的個人頁面 |
| 👥 好友系統 | 查看好友的演唱會紀錄與關注清單 |
| ⚙️ 通知設定 | 自選通知方式、設定勿擾時段 |
| 🤖 Discord 互動端點 | 透過 HTTP Interactions 接收 slash command |

---

## 支援平台

| 平台 | 網域 |
|---|---|
| **KKTIX** | kktix.com |
| **TixCraft** | tixcraft.com |
| **拓元 Ticket Plus** | ticket.com.tw |
| **ibon 7-ELEVEN** | ibon.7-eleven.com.tw |
| **寬宏藝術 Kham** | kham.com.tw |

---

## 技術架構

| 層級 | 技術 |
|---|---|
| 語言 | Python 3.11+ |
| Web 框架 | FastAPI + Jinja2 + Vanilla JS |
| Discord Bot | discord.py v2.x |
| Discord Interactions | FastAPI HTTP 端點（Ed25519 驗證） |
| 資料庫 | PostgreSQL 16（SQLAlchemy async ORM） |
| 排程 | APScheduler |
| 通知 | Discord DM / SMTP / SendGrid |
| 驗證 | Discord OAuth2 |
| 部署 | Docker + Docker Compose |

---

## 首次啟動（從零開始）

### Step 1 — 確認環境

確認以下工具已安裝並正常運作：

```bash
python --version       # 需要 3.11 以上
docker --version       # Docker Desktop 需已啟動
docker compose version
```

若尚未安裝 Docker，請至 [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop) 下載安裝，並確認 Docker Desktop 已開啟。

---

### Step 2 — 取得 Discord 憑證

前往 [discord.com/developers/applications](https://discord.com/developers/applications)，選擇你的應用程式。

| 到哪個頁面 | 需要取得的值 |
|---|---|
| General Information | **Application ID**（即 Client ID） |
| General Information | **Public Key** |
| OAuth2 → General | **Client Secret**（點 Reset 產生） |
| Bot | **Bot Token**（點 Reset Token 產生） |

> ⚠️ Token 與 Secret 只會顯示一次，請立刻複製並妥善保存。

---

### Step 3 — 建立 .env 檔案

複製範本：

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

用文字編輯器開啟 `.env`，**至少填入以下必填欄位**：

```env
# ── Discord（必填）──────────────────────────────────────
DISCORD_BOT_TOKEN=           # Bot 頁面取得的 Token
DISCORD_CLIENT_ID=1483021120881033279
DISCORD_CLIENT_SECRET=       # OAuth2 頁面取得的 Secret
DISCORD_PUBLIC_KEY=7ecd745ac9ae4b6f6dd475f82855caed69e88ba1aafc72e36dd066cfc013dca2
DISCORD_REDIRECT_URI=http://localhost:8000/auth/callback

# ── App（必填）─────────────────────────────────────────
APP_SECRET_KEY=               # 隨意填一串亂碼，例如：tp-secret-xk29djf8
APP_BASE_URL=http://localhost:8000

# ── 其餘維持預設值即可 ──────────────────────────────────
DATABASE_URL=postgresql+asyncpg://ticketpulse:ticketpulse@localhost:5432/ticketpulse
REDIS_URL=redis://localhost:6379
DEBUG=true
SCRAPER_INTERVAL_SECONDS=60
```

> Email 相關欄位可暫時留空，之後再填（詳見 [Email 通知設定](#email-通知設定)）。

---

### Step 4 — 設定 Discord OAuth2 Redirect URI

回到 Discord Developer Portal：

**OAuth2 → Redirects → Add Redirect**

填入：
```
http://localhost:8000/auth/callback
```

點 **Save Changes**。

---

### Step 5 — 啟動所有服務

在專案根目錄執行：

```bash
docker compose up --build
```

Docker 會自動啟動以下容器：

| 容器 | 服務 | Port |
|---|---|---|
| `db` | PostgreSQL 資料庫 | 5432 |
| `redis` | Redis | 6379 |
| `web` | FastAPI 網頁 + API | 8000 |
| `bot` | Discord Bot | — |

**首次執行約需 3–5 分鐘**（下載 image + 安裝套件）。

出現以下訊息即表示啟動成功：

```
web-1  | INFO:     Application startup complete.
bot-1  | INFO  bot_ready user=TicketPulse#xxxx
```

若要在背景執行：

```bash
docker compose up -d --build
```

查看背景執行的 log：

```bash
docker compose logs -f
```

停止所有服務：

```bash
docker compose down
```

---

### Step 6 — 開啟網頁

瀏覽器前往：

```
http://localhost:8000
```

點擊「**使用 Discord 登入**」，完成帳號連結後即可使用所有功能。

---

### Step 7 — 邀請 Bot 到 Discord 伺服器

使用以下連結邀請 Bot 加入伺服器：

```
https://discord.com/api/oauth2/authorize?client_id=1483021120881033279&permissions=274877991936&scope=bot%20applications.commands
```

選擇目標伺服器後，Slash Commands 會自動同步（最長等待 1 小時，重啟 Bot 容器可加速）。

---

### Step 8 — 設定 Interactions Endpoint（選用）

此步驟讓 Discord 透過 HTTP 將 slash command 傳送到你的伺服器，**適合對外部署使用**。

**本機開發可使用 ngrok 暫時測試：**

```bash
# 另開一個終端
ngrok http 8000
```

複製產生的 HTTPS 網址（例如 `https://abc123.ngrok-free.app`）。

回到 Discord Developer Portal：

**General Information → Interactions Endpoint URL**

```
https://abc123.ngrok-free.app/interactions
```

點 **Save Changes**，Discord 會自動向該端點發送 PING 驗證，通過後即完成設定。

> 正式部署時，將 ngrok 換成你的實際網域，並同步更新 `.env` 中的 `APP_BASE_URL`。

---

## Email 通知設定

### 方式一：Gmail SMTP

1. 開啟 Google 帳號的[兩步驟驗證](https://myaccount.google.com/security)
2. 前往[應用程式密碼](https://myaccount.google.com/apppasswords)，產生一組專用密碼
3. 填入 `.env`：

```env
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USERNAME=你的帳號@gmail.com
EMAIL_PASSWORD=產生的應用程式密碼（非 Google 登入密碼）
EMAIL_FROM=TicketPulse <你的帳號@gmail.com>
```

### 方式二：SendGrid

```env
SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxx
EMAIL_FROM=TicketPulse <no-reply@你的網域.com>
```

> 填入後重啟服務（`docker compose restart web`）。
> 使用者在網頁「個人資料 → 通知設定」選擇 `Email` 或 `Discord DM + Email` 即可啟用。

---

## 使用說明

### 網頁功能

| 頁面 | 網址 | 說明 |
|---|---|---|
| 首頁 / Dashboard | `/` | 登入後顯示關注清單與歷史紀錄摘要 |
| 關注清單 | `/watchlist` | 貼上售票網址新增追蹤、查看狀態、移除 |
| 演唱會歷史 | `/history` | 新增與查看已參加或錯過的演唱會紀錄 |
| 個人資料 | `/profile` | 查看個人統計、設定通知方式與隱私 |
| 他人資料 | `/profile/{discord_id}` | 查看其他使用者的公開資料 |
| API 文件 | `/api/docs` | Swagger UI（`DEBUG=true` 時可用） |

### 新增關注清單

1. 前往 `/watchlist`
2. 貼上售票頁面完整網址，例如：
   ```
   https://kktix.com/events/xxx
   https://tixcraft.com/activity/12345
   ```
3. 點「**+ 加入關注**」，系統自動抓取演唱會資訊並開始監控

### 票券狀態說明

| 狀態 | 說明 |
|---|---|
| 👀 關注中 | 正在監控，票券尚未開售 |
| 🔔 已通知 | 票券已開售，通知已發出 |
| 💤 已過期 | 監控已結束 |

### 演唱會歷史狀態說明

| 狀態 | 說明 |
|---|---|
| ✅ 已參加 | 成功購票並出席 |
| ❌ 未參加 | 未購到票或錯過 |
| 👀 追蹤中 | 尚在追蹤或觀察中 |

---

## Discord Bot 指令

Bot 提供以下輕量 Slash Commands，主要操作請使用網頁：

| 指令 | 說明 |
|---|---|
| `/status` | 查看帳號連結狀態與目前關注數量 |
| `/watchlist` | 查看關注清單摘要（最多 5 筆）+ 網頁連結 |
| `/link` | 取得網頁版連結，快速導向完整功能 |
| `/alert-test` | 發送測試通知（需「管理伺服器」權限） |

---

## 專案結構

```
TicketPulse/
├── bot/                        # Discord Bot（通知 + 簡單指令）
│   ├── main.py                 # Bot 進入點
│   ├── cogs/
│   │   ├── alerts.py           # 提醒頻道管理（管理員）
│   │   ├── watchlist.py        # 關注清單共用邏輯
│   │   ├── history.py          # 歷史紀錄指令
│   │   ├── profile.py          # 個人資料指令
│   │   ├── friends.py          # 好友系統指令
│   │   └── settings.py         # 個人設定指令
│   └── utils/
│       ├── embeds.py           # Discord Embed 範本
│       └── checks.py           # 權限檢查
│
├── web/                        # Web App（主要使用介面）
│   ├── main.py                 # FastAPI 進入點
│   ├── routers/
│   │   ├── auth.py             # Discord OAuth2 登入
│   │   ├── interactions.py     # Discord HTTP Interactions 端點
│   │   ├── profile.py          # 個人資料 & 好友 API
│   │   ├── history.py          # 歷史紀錄 API
│   │   └── watchlist.py        # 關注清單 API
│   ├── templates/              # Jinja2 HTML 頁面
│   │   ├── base.html           # 共用版型（Navbar、Footer）
│   │   ├── index.html          # 首頁 / Dashboard
│   │   ├── watchlist.html      # 關注清單頁面
│   │   ├── history.html        # 演唱會歷史頁面
│   │   └── profile.html        # 個人資料頁面
│   └── static/
│       ├── css/style.css       # 深色主題 RWD 樣式
│       └── js/app.js           # 前端 JS（Toast、fetch）
│
├── scraper/                    # 票券監控引擎
│   ├── base.py                 # 抽象爬蟲基底類別 + TicketInfo
│   ├── kktix.py                # KKTIX 爬蟲（JSON API）
│   ├── tixcraft.py             # TixCraft 爬蟲（HTML）
│   ├── ticket_plus.py          # 拓元爬蟲（AJAX）
│   ├── ibon.py                 # ibon 爬蟲
│   ├── kham.py                 # 寬宏藝術爬蟲
│   └── scheduler.py            # APScheduler 輪詢排程
│
├── db/
│   ├── models.py               # SQLAlchemy ORM 模型
│   ├── crud.py                 # 所有資料庫操作（唯一入口）
│   └── session.py              # 非同步 Session 管理
│
├── core/
│   ├── config.py               # pydantic-settings（所有環境變數）
│   ├── notifier.py             # 通知派發器（Discord + Email）
│   └── logger.py               # 結構化日誌（structlog）
│
├── tests/
│   ├── test_crud.py            # CRUD 整合測試
│   └── test_scrapers.py        # 爬蟲解析單元測試
│
├── .env.example                # 環境變數範本
├── .env                        # 實際設定檔（不進 git）
├── docker-compose.yml
├── Dockerfile
├── pytest.ini
├── requirements.txt
└── README.md
```

---

## 開發指南

### 不使用 Docker 的本機執行方式

確認本機已安裝並啟動 PostgreSQL 與 Redis，然後：

```bash
# 安裝 Python 依賴
pip install -r requirements.txt

# 終端 1 — Web App
uvicorn web.main:app --reload --port 8000

# 終端 2 — Discord Bot
python -m bot.main
```

### 執行測試

```bash
# 先建立測試資料庫
createdb ticketpulse_test

# 執行全部測試
pytest

# 只跑爬蟲解析測試（不需要資料庫）
pytest tests/test_scrapers.py -v
```

### 新增售票平台爬蟲

1. 在 `scraper/` 新建 `平台名稱.py`
2. 繼承 `BaseScraper`，實作 `fetch(url) -> TicketInfo | None`
3. 在 `scraper/scheduler.py` 的 `_SCRAPERS` dict 中加入新平台
4. 在 `bot/cogs/watchlist.py` 的 `_detect_platform()` 加入 URL 判斷規則

### 新增 Discord Slash Command

1. 在 `web/routers/interactions.py` 的 `_handle_command()` 加入新 `case`
2. 實作對應的 `async def _cmd_xxx()` 函式
3. 在 Discord Developer Portal → Bot → Slash Commands 手動新增該指令

---

## 常見問題

**Q: `web` 容器持續重啟，log 顯示 `ValidationError`**
A: `.env` 中有必填欄位未填，最常見是 `DISCORD_BOT_TOKEN` 或 `APP_SECRET_KEY` 留空。

**Q: Discord 登入後跳回首頁但未顯示登入狀態**
A: 確認 Discord Developer Portal 的 Redirect URI 與 `.env` 的 `DISCORD_REDIRECT_URI` **完全一致**（協定、域名、路徑、斜線均需相同）。

**Q: Slash Command 在 Discord 中沒有出現**
A: 全球同步最長需 1 小時；重啟 Bot 容器（`docker compose restart bot`）可加速。邀請 Bot 時確認已包含 `applications.commands` scope。

**Q: 連線資料庫失敗（`asyncpg` 錯誤）**
A: `DATABASE_URL` 前綴必須使用 `postgresql+asyncpg://`，不是 `postgresql://`。

**Q: Interactions Endpoint 在 Discord Portal 無法儲存**
A: 確認 Web App 正常運行、ngrok 轉發中，且 `DISCORD_PUBLIC_KEY` 與 Portal 上的值完全一致。

**Q: Email 通知沒有收到**
A: 使用 Gmail 時必須產生「應用程式密碼」，不可直接用 Google 登入密碼。確認帳號已開啟兩步驟驗證。

**Q: 如何完整清除資料重新開始**

```bash
docker compose down -v   # 停止並刪除所有 volume（包含資料庫資料）
docker compose up --build
```

---

## Discord Bot 資訊

| 欄位 | 值 |
|---|---|
| Bot ID | `1483021120881033279` |
| Public Key | `7ecd745ac9ae4b6f6dd475f82855caed69e88ba1aafc72e36dd066cfc013dca2` |
| Interactions Endpoint URL | `https://<your-domain>/interactions` |

---

## License

MIT
