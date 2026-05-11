# Telegram Store Manager

Production-ready Telegram bot and Mini App for managing a fashion store catalog, product availability, channel posts, discounts, orders, and inventory.

The project combines an aiogram bot, PostgreSQL storage, Redis FSM, a FastAPI backend, and a React/Vite Telegram Mini App. It is designed for stores that sell clothing, shoes, and accessories through Telegram.

## Features

- Product catalog with categories, photos, prices, sizes, descriptions, and availability status.
- Telegram admin panel with FSM workflows for adding products, collecting 1-5 photos, editing drafts, and publishing items.
- Channel publishing for product posts, media groups, discount updates, and SOLD status.
- Import from Telegram channel posts into the bot catalog.
- Discount management with old price and current price display.
- SOLD workflow that removes products from the public catalog and keeps admin history.
- Telegram Mini App storefront with search, categories, sorting, favorites, cart, and checkout.
- Order creation through the Mini App with admin notifications in Telegram.
- PostgreSQL migrations with Alembic and structured logging for production use.

## Tech Stack

- Python 3.13+
- aiogram 3.x
- FastAPI
- PostgreSQL
- Redis
- SQLAlchemy 2.x
- Alembic
- React
- Vite
- TypeScript
- Zustand
- Caddy
- Docker Compose

## Project Structure

```text
app/
  handlers/          Telegram bot handlers
  keyboards/         Reply and inline keyboards
  database/          SQLAlchemy models, sessions, repositories
  services/          Product, channel, order, and formatting services
  states/            FSM states
  utils/             Logging and premium emoji helpers
  web/               FastAPI Mini App API

frontend/
  src/
    api/             API client
    components/      Storefront UI components
    pages/           Mini App pages
    store/           Cart and favorites state
    types/           TypeScript types
    utils/           Telegram WebApp helpers

alembic/             Database migrations
scripts/             Deployment and bootstrap helpers
tests/               Unit and service tests
```

## Environment Variables

Copy the example file and fill it with your own values:

```bash
cp .env.example .env
```

Example:

```env
BOT_TOKEN=your_bot_token_here
ADMIN_IDS=123456789
CHANNEL_ID=-1001234567890

SUPPORT_USERNAME=your_support_username
SUPPORT_URL=https://t.me/your_support_username
REVIEWS_URL=https://t.me/your_reviews_channel
TIKTOK_URL=https://www.tiktok.com/@your_store
LOGISTICS_URL=https://t.me/your_channel/1

MINI_APP_URL=https://example.com/app
CADDY_SITE_ADDRESS=:8080

POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=store_manager
POSTGRES_USER=store_manager
POSTGRES_PASSWORD=your_password_here

REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

LOG_LEVEL=INFO
```

Use `MINI_APP_URL=http://<ip>:8080/app` for temporary server testing through an IP address. For a real Telegram Mini App, use an HTTPS domain and configure it in BotFather.

## Installation

Create a virtual environment and install the Python package:

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e .[dev]
```

Apply database migrations:

```bash
alembic upgrade head
```

Run the Telegram bot:

```bash
python -m app.main
```

Run the Mini App backend:

```bash
python -m uvicorn app.web.main:app --reload --host 127.0.0.1 --port 8000
```

Run the frontend in development mode:

```bash
cd frontend
npm install
npm run dev
```

## Run With Docker

Start the full stack:

```bash
docker compose up --build -d
```

Services:

- `postgres` - product and order database
- `redis` - FSM storage
- `migrate` - Alembic migrations
- `bot` - Telegram bot long polling
- `backend` - FastAPI Mini App API
- `web` - Caddy static frontend and `/api` reverse proxy

Useful commands:

```bash
docker compose ps
docker compose logs -f bot
docker compose logs -f backend
docker compose logs -f web
```

Local URLs:

- Mini App frontend: `http://127.0.0.1:8080/app`
- API health check: `http://127.0.0.1:8080/api/health`

Server test URLs:

- Mini App frontend: `http://<ip>:8080/app`
- API health check: `http://<ip>:8080/api/health`

## Mini App API

- `GET /api/products` - list active products from the same database used by the bot.
- `GET /api/products/{id}` - get one product.
- `GET /api/categories` - list product categories.
- `GET /api/meta` - public storefront metadata and links.
- `POST /api/webapp/validate` - validate Telegram WebApp `initData`.
- `POST /api/orders` - create an order and notify admins.
- `GET /api/media/{photo_id}` - proxy Telegram product photos without exposing the bot token to the frontend.

## Security Notes

- Never commit `.env`.
- Never publish real bot tokens, admin IDs, channel IDs, passwords, server IPs, private domains, or private Telegram links.
- Keep production credentials only on the deployment server.
- Use `.env.example` only for safe placeholder values.
- Review files with a secret scan before publishing changes.

## Tests

```bash
python -m pytest
```

Frontend build:

```bash
cd frontend
npm run build
```
