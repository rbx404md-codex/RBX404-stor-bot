"""
SQLite schema. Only metadata lives here — actual product files always stay
in the Telegram storage channel; we only store channel_id + message_id.
"""
import os
import aiosqlite

from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id         INTEGER PRIMARY KEY,
    username        TEXT,
    coin_balance    INTEGER NOT NULL DEFAULT 0,
    total_purchases INTEGER NOT NULL DEFAULT 0,
    referral_code   TEXT UNIQUE,
    referred_by     INTEGER,
    language        TEXT NOT NULL DEFAULT 'bn',
    is_banned       INTEGER NOT NULL DEFAULT 0,
    is_muted        INTEGER NOT NULL DEFAULT 0,
    is_premium       INTEGER NOT NULL DEFAULT 0,
    notes            TEXT NOT NULL DEFAULT '',
    last_seen_at     TEXT,
    joined_at       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS categories (
    category_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    icon        TEXT NOT NULL DEFAULT '📦',
    sort_order  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS products (
    product_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id   INTEGER,
    name          TEXT NOT NULL,
    description   TEXT NOT NULL DEFAULT '',
    price_coin    INTEGER NOT NULL DEFAULT 0,
    price_stars   INTEGER NOT NULL DEFAULT 0,
    storage_msg_id INTEGER NOT NULL,     -- message_id inside STORAGE_CHANNEL_ID
    preview_msg_id INTEGER,              -- optional preview/thumbnail message_id
    is_active     INTEGER NOT NULL DEFAULT 1,
    is_featured   INTEGER NOT NULL DEFAULT 0,
    sales_count   INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (category_id) REFERENCES categories(category_id)
);

CREATE TABLE IF NOT EXISTS orders (
    order_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        INTEGER NOT NULL,
    product_id     INTEGER NOT NULL,
    payment_method TEXT NOT NULL,        -- 'coin' | 'stars'
    amount_paid    INTEGER NOT NULL,
    coupon_code    TEXT,
    external_payment_id TEXT,
    status         TEXT NOT NULL DEFAULT 'completed',   -- completed | refunded | failed
    created_at     TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE TABLE IF NOT EXISTS coin_transactions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    amount     INTEGER NOT NULL,          -- positive = credit, negative = debit
    reason     TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS topup_requests (
    request_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id          INTEGER NOT NULL,
    payment_method   TEXT NOT NULL,        -- 'bkash' | 'nagad'
    paid_bdt         INTEGER NOT NULL,
    coin_amount      INTEGER NOT NULL,
    transaction_id   TEXT NOT NULL UNIQUE,
    status           TEXT NOT NULL DEFAULT 'pending', -- pending | approved | rejected
    reviewed_by      INTEGER,
    reviewed_at      TEXT,
    created_at       TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS referrals (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    referrer_id   INTEGER NOT NULL,
    referred_id   INTEGER NOT NULL UNIQUE,
    status        TEXT NOT NULL DEFAULT 'pending',
    verified_at   TEXT,
    last_checked_at TEXT,
    invalid_reason TEXT,
    reward_given  INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS shared_links (
    token           TEXT PRIMARY KEY,
    owner_id        INTEGER NOT NULL,
    content_type    TEXT NOT NULL,
    file_id         TEXT,
    text_content    TEXT,
    file_name       TEXT,
    mime_type       TEXT,
    expires_at      TEXT,
    one_time        INTEGER NOT NULL DEFAULT 0,
    max_views       INTEGER NOT NULL DEFAULT 0,
    views           INTEGER NOT NULL DEFAULT 0,
    password_hash   TEXT,
    is_active       INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    last_accessed_at TEXT,
    FOREIGN KEY (owner_id) REFERENCES users(user_id)
);

CREATE INDEX IF NOT EXISTS idx_shared_links_owner ON shared_links(owner_id);
CREATE INDEX IF NOT EXISTS idx_shared_links_active ON shared_links(is_active, expires_at);

CREATE TABLE IF NOT EXISTS coupons (
    code           TEXT PRIMARY KEY,
    discount_type  TEXT NOT NULL,          -- 'percent' | 'fixed_coin'
    discount_value INTEGER NOT NULL,
    usage_limit    INTEGER NOT NULL DEFAULT 0,   -- 0 = unlimited
    used_count     INTEGER NOT NULL DEFAULT 0,
    expires_at     TEXT,
    is_active      INTEGER NOT NULL DEFAULT 1,
    created_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS coupon_usage (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    code        TEXT NOT NULL,
    user_id     INTEGER NOT NULL,
    used_at     TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(code, user_id)
);

CREATE TABLE IF NOT EXISTS admin_logs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id   INTEGER NOT NULL,
    action     TEXT NOT NULL,
    details    TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS app_settings (
    setting_key   TEXT PRIMARY KEY,
    setting_value TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS force_join_channels (
    channel_id  INTEGER PRIMARY KEY,
    title       TEXT NOT NULL,
    invite_link TEXT NOT NULL,
    is_active   INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS wishlists (
    user_id    INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, product_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE TABLE IF NOT EXISTS reviews (
    review_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    rating     INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    review     TEXT NOT NULL DEFAULT '',
    is_visible INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, product_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE TABLE IF NOT EXISTS daily_checkins (
    user_id      INTEGER NOT NULL,
    checkin_date TEXT NOT NULL,
    reward_coins INTEGER NOT NULL,
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, checkin_date),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS support_tickets (
    ticket_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    message    TEXT NOT NULL,
    status     TEXT NOT NULL DEFAULT 'open',
    admin_id   INTEGER,
    reply      TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS notifications (
    notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    kind            TEXT NOT NULL,
    title           TEXT NOT NULL,
    body            TEXT NOT NULL,
    is_read         INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS scheduled_broadcasts (
    broadcast_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id        INTEGER NOT NULL,
    message_id      INTEGER NOT NULL,
    chat_id         INTEGER NOT NULL,
    scheduled_at    TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending',
    sent_count      INTEGER NOT NULL DEFAULT 0,
    failed_count    INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS user_activity (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    activity        TEXT NOT NULL,
    metadata        TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
"""


async def init_db() -> None:
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        migrations = (
            "ALTER TABLE products ADD COLUMN is_featured INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE users ADD COLUMN is_muted INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE users ADD COLUMN is_premium INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE users ADD COLUMN notes TEXT NOT NULL DEFAULT ''",
            "ALTER TABLE users ADD COLUMN last_seen_at TEXT",
            "ALTER TABLE orders ADD COLUMN external_payment_id TEXT",
            "ALTER TABLE referrals ADD COLUMN status TEXT NOT NULL DEFAULT 'pending'",
            "ALTER TABLE referrals ADD COLUMN verified_at TEXT",
            "ALTER TABLE referrals ADD COLUMN last_checked_at TEXT",
            "ALTER TABLE referrals ADD COLUMN invalid_reason TEXT",
        )
        for statement in migrations:
            try:
                await db.execute(statement)
            except aiosqlite.OperationalError:
                pass
        await db.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_external_payment "
            "ON orders(external_payment_id) WHERE external_payment_id IS NOT NULL"
        )
        await db.commit()


def get_conn() -> aiosqlite.Connection:
    """Each caller should `async with get_conn() as db:`."""
    return aiosqlite.connect(DB_PATH)
