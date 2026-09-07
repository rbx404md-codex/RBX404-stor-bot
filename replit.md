# RBX404 Digital Store Bot

Telegram-based digital store bot with secure file delivery, wallets, referrals, force-join gating, share links, and a branded mini portal.

## Run & Operate

- `pnpm --filter @workspace/api-server run dev` — run the API server (port 5000)
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from the OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- Required env: `DATABASE_URL` — Postgres connection string
- Bot runtime: `cd bot-project && pip install -r requirements.txt && cp .env.example .env && python main.py`
- Docker runtime: `cd bot-project && docker compose up -d`
- Termux/VPS watchdog: `cd bot-project && ./run.sh` or `./watchdog.sh`

## Stack

- pnpm workspaces, Node.js 24, TypeScript 5.9
- API: Express 5
- DB: PostgreSQL + Drizzle ORM
- Validation: Zod (`zod/v4`), `drizzle-zod`
- API codegen: Orval (from OpenAPI spec)
- Build: esbuild (CJS bundle)

## Where things live

- `bot-project/handlers/` — Telegram user, checkout, referral, force-join, linkgen, and admin flows
- `bot-project/database/models.py` — SQLite schema and forward-compatible migrations
- `bot-project/database/queries.py` — parameterized database access and analytics helpers
- `bot-project/web_portal.py` — password/expiry/view-limited public share portal
- `bot-project/utils/branding.py` — Unicode fallback and optional Telegram custom emoji transport
- `bot-project/Dockerfile` and `bot-project/docker-compose.yml` — portable deployment

## Architecture decisions

- Product files remain in a private Telegram storage channel; SQLite stores only message IDs and metadata.
- All user-generated text is kept out of HTML formatting paths unless explicitly escaped.
- Stars payments are idempotent using Telegram's charge ID, preventing duplicate delivery on retries.
- Share links expose opaque database tokens only; raw Telegram file IDs stay server-side.
- Custom emoji are transport-level enhancements with Unicode fallback so missing IDs never break messages.

## Product

RBX404 supports a multilingual Telegram store with Coin and Telegram Stars checkout, automatic digital delivery, manual top-ups, coupons, wishlists, reviews, support tickets, referral rewards, force-join verification, universal share links, and an admin control surface.

## User preferences

- The next planned pass is to map the supplied Telegram premium custom emoji IDs to the branded UI roles.

## Gotchas

- Never put a real `BOT_TOKEN`, admin ID, or channel ID in `.env.example`, source files, or public archives.
- The bot needs admin access to every force-join chat and the private storage/backup channels.
- Run the bot from `bot-project/` so relative paths such as `data/bot.db` resolve correctly.
- Set `BASE_URL` to the public portal origin before using `/linkgen` outside local development.

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
