"""
All database access goes through these helpers so handlers never write raw
SQL. Keeping it in one place also makes the backup/restore story simple —
the whole app's state is this one sqlite file.
"""
import secrets
import string
from datetime import datetime, timezone

from database.models import get_conn


def _gen_ref_code() -> str:
    return "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(7))


# ---------------------------------------------------------------- users ----
async def get_or_create_user(user_id: int, username: str | None, referred_by_code: str | None = None) -> dict:
    async with get_conn() as db:
        db.row_factory = None
        cur = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        if row:
            await db.execute(
                "UPDATE users SET username=?, last_seen_at=datetime('now') WHERE user_id=?",
                (username, user_id),
            )
            await db.commit()
            cur = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = await cur.fetchone()
            cols = [d[0] for d in cur.description]
            return dict(zip(cols, row))

        ref_code = _gen_ref_code()
        referred_by = None
        if referred_by_code:
            cur2 = await db.execute("SELECT user_id FROM users WHERE referral_code = ?", (referred_by_code,))
            r = await cur2.fetchone()
            if r and r[0] != user_id:
                referred_by = r[0]

        await db.execute(
            "INSERT INTO users (user_id, username, referral_code, referred_by) VALUES (?,?,?,?)",
            (user_id, username, ref_code, referred_by),
        )
        if referred_by:
            await db.execute(
                "INSERT OR IGNORE INTO referrals (referrer_id, referred_id) VALUES (?,?)",
                (referred_by, user_id),
            )
        await db.commit()

        cur = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))


async def get_user(user_id: int) -> dict | None:
    async with get_conn() as db:
        cur = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        if not row:
            return None
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))


async def set_ban(user_id: int, banned: bool) -> None:
    async with get_conn() as db:
        await db.execute("UPDATE users SET is_banned = ? WHERE user_id = ?", (int(banned), user_id))
        await db.commit()


async def touch_user(user_id: int, activity: str = "message", metadata: str | None = None) -> None:
    """Update lightweight activity information without storing message content."""
    async with get_conn() as db:
        await db.execute(
            "UPDATE users SET last_seen_at=datetime('now') WHERE user_id=?",
            (user_id,),
        )
        await db.execute(
            "INSERT INTO user_activity (user_id, activity, metadata) VALUES (?,?,?)",
            (user_id, activity, metadata),
        )
        await db.commit()


async def set_user_language(user_id: int, language: str) -> None:
    if language not in {"bn", "en", "hi", "ur", "ru", "ar"}:
        raise ValueError("Unsupported language")
    async with get_conn() as db:
        await db.execute("UPDATE users SET language=? WHERE user_id=?", (language, user_id))
        await db.commit()


async def set_user_muted(user_id: int, muted: bool) -> None:
    async with get_conn() as db:
        await db.execute("UPDATE users SET is_muted=? WHERE user_id=?", (int(muted), user_id))
        await db.commit()


async def set_user_premium(user_id: int, premium: bool) -> None:
    async with get_conn() as db:
        await db.execute("UPDATE users SET is_premium=? WHERE user_id=?", (int(premium), user_id))
        await db.commit()


async def update_user_notes(user_id: int, notes: str) -> None:
    async with get_conn() as db:
        await db.execute("UPDATE users SET notes=? WHERE user_id=?", (notes[:2000], user_id))
        await db.commit()


# ---------------------------------------------------------------- coins ----
async def adjust_coins(user_id: int, amount: int, reason: str) -> int:
    """amount can be negative. Returns new balance. Raises ValueError if insufficient."""
    async with get_conn() as db:
        cur = await db.execute("SELECT coin_balance FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        balance = row[0] if row else 0
        new_balance = balance + amount
        if new_balance < 0:
            raise ValueError("Insufficient coin balance")

        await db.execute("UPDATE users SET coin_balance = ? WHERE user_id = ?", (new_balance, user_id))
        await db.execute(
            "INSERT INTO coin_transactions (user_id, amount, reason) VALUES (?,?,?)",
            (user_id, amount, reason),
        )
        await db.commit()
        return new_balance


async def create_topup_request(user_id: int, payment_method: str, paid_bdt: int,
                               coin_amount: int, transaction_id: str) -> int | None:
    """Create a pending top-up; transaction IDs cannot be reused."""
    async with get_conn() as db:
        try:
            cur = await db.execute(
                "INSERT INTO topup_requests "
                "(user_id, payment_method, paid_bdt, coin_amount, transaction_id) "
                "VALUES (?,?,?,?,?)",
                (user_id, payment_method, paid_bdt, coin_amount, transaction_id),
            )
            await db.commit()
            return cur.lastrowid
        except Exception as exc:
            await db.rollback()
            if "UNIQUE constraint failed" in str(exc):
                return None
            raise


async def pending_topup_requests(limit: int = 30) -> list[dict]:
    async with get_conn() as db:
        cur = await db.execute(
            "SELECT t.*, u.username FROM topup_requests t "
            "LEFT JOIN users u ON u.user_id = t.user_id "
            "WHERE t.status = 'pending' ORDER BY t.request_id ASC LIMIT ?",
            (limit,),
        )
        rows = await cur.fetchall()
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in rows]


async def get_topup_request(request_id: int) -> dict | None:
    async with get_conn() as db:
        cur = await db.execute(
            "SELECT t.*, u.username FROM topup_requests t "
            "LEFT JOIN users u ON u.user_id = t.user_id "
            "WHERE t.request_id = ?",
            (request_id,),
        )
        row = await cur.fetchone()
        if not row:
            return None
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))


async def user_topup_requests(user_id: int, limit: int = 10) -> list[dict]:
    async with get_conn() as db:
        cur = await db.execute(
            "SELECT request_id, payment_method, paid_bdt, coin_amount, transaction_id, "
            "status, reviewed_at, created_at FROM topup_requests "
            "WHERE user_id = ? ORDER BY request_id DESC LIMIT ?",
            (user_id, limit),
        )
        rows = await cur.fetchall()
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in rows]


async def approve_topup_request(request_id: int, admin_id: int) -> dict | None:
    """Approve and credit a request atomically; returns None if already reviewed."""
    async with get_conn() as db:
        await db.execute("BEGIN IMMEDIATE")
        cur = await db.execute(
            "SELECT user_id, coin_amount, transaction_id FROM topup_requests "
            "WHERE request_id = ? AND status = 'pending'",
            (request_id,),
        )
        row = await cur.fetchone()
        if not row:
            await db.rollback()
            return None

        user_id, coin_amount, transaction_id = row
        cur = await db.execute("SELECT coin_balance FROM users WHERE user_id = ?", (user_id,))
        user_row = await cur.fetchone()
        if not user_row:
            await db.rollback()
            return None
        new_balance = user_row[0] + coin_amount
        reviewed_at = datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")
        await db.execute(
            "UPDATE topup_requests SET status='approved', reviewed_by=?, reviewed_at=? "
            "WHERE request_id=? AND status='pending'",
            (admin_id, reviewed_at, request_id),
        )
        await db.execute("UPDATE users SET coin_balance=? WHERE user_id=?", (new_balance, user_id))
        await db.execute(
            "INSERT INTO coin_transactions (user_id, amount, reason) VALUES (?,?,?)",
            (user_id, coin_amount, f"Top-up approved: {transaction_id}"),
        )
        await db.execute(
            "INSERT INTO admin_logs (admin_id, action, details) VALUES (?,?,?)",
            (admin_id, "approve_topup", f"request_id={request_id}, user_id={user_id}"),
        )
        await db.commit()
        return {
            "request_id": request_id,
            "user_id": user_id,
            "coin_amount": coin_amount,
            "transaction_id": transaction_id,
            "new_balance": new_balance,
        }


async def reject_topup_request(request_id: int, admin_id: int) -> dict | None:
    async with get_conn() as db:
        await db.execute("BEGIN IMMEDIATE")
        cur = await db.execute(
            "SELECT user_id, coin_amount, transaction_id FROM topup_requests "
            "WHERE request_id = ? AND status = 'pending'",
            (request_id,),
        )
        row = await cur.fetchone()
        if not row:
            await db.rollback()
            return None
        user_id, coin_amount, transaction_id = row
        reviewed_at = datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")
        await db.execute(
            "UPDATE topup_requests SET status='rejected', reviewed_by=?, reviewed_at=? "
            "WHERE request_id=? AND status='pending'",
            (admin_id, reviewed_at, request_id),
        )
        await db.execute(
            "INSERT INTO admin_logs (admin_id, action, details) VALUES (?,?,?)",
            (admin_id, "reject_topup", f"request_id={request_id}, user_id={user_id}"),
        )
        await db.commit()
        return {
            "request_id": request_id,
            "user_id": user_id,
            "coin_amount": coin_amount,
            "transaction_id": transaction_id,
        }


async def coin_history(user_id: int, limit: int = 15) -> list[dict]:
    async with get_conn() as db:
        cur = await db.execute(
            "SELECT amount, reason, created_at FROM coin_transactions "
            "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        )
        rows = await cur.fetchall()
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in rows]


# ----------------------------------------------------------- categories ----
async def list_categories() -> list[dict]:
    async with get_conn() as db:
        cur = await db.execute("SELECT * FROM categories ORDER BY sort_order, name")
        rows = await cur.fetchall()
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in rows]


async def add_category(name: str, icon: str = "📦") -> int:
    async with get_conn() as db:
        cur = await db.execute("INSERT INTO categories (name, icon) VALUES (?,?)", (name, icon))
        await db.commit()
        return cur.lastrowid


# -------------------------------------------------------------- products ---
async def list_products(category_id: int | None = None, active_only: bool = True,
                        limit: int | None = None, offset: int = 0) -> list[dict]:
    q = "SELECT * FROM products WHERE 1=1"
    params: list = []
    if category_id is not None:
        q += " AND category_id = ?"
        params.append(category_id)
    if active_only:
        q += " AND is_active = 1"
    q += " ORDER BY is_featured DESC, sales_count DESC, product_id DESC"
    if limit is not None:
        q += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])
    async with get_conn() as db:
        cur = await db.execute(q, params)
        rows = await cur.fetchall()
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in rows]


async def get_product(product_id: int) -> dict | None:
    async with get_conn() as db:
        cur = await db.execute("SELECT * FROM products WHERE product_id = ?", (product_id,))
        row = await cur.fetchone()
        if not row:
            return None
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))


async def add_product(category_id: int, name: str, description: str, price_coin: int,
                       price_stars: int, storage_msg_id: int, preview_msg_id: int | None = None) -> int:
    async with get_conn() as db:
        cur = await db.execute(
            "INSERT INTO products (category_id, name, description, price_coin, price_stars, "
            "storage_msg_id, preview_msg_id) VALUES (?,?,?,?,?,?,?)",
            (category_id, name, description, price_coin, price_stars, storage_msg_id, preview_msg_id),
        )
        await db.commit()
        return cur.lastrowid


async def set_product_active(product_id: int, active: bool) -> None:
    async with get_conn() as db:
        await db.execute("UPDATE products SET is_active = ? WHERE product_id = ?", (int(active), product_id))
        await db.commit()


async def bump_sales(product_id: int) -> None:
    async with get_conn() as db:
        await db.execute("UPDATE products SET sales_count = sales_count + 1 WHERE product_id = ?", (product_id,))
        await db.commit()


# ----------------------------------------------------------------- orders --
async def create_order(user_id: int, product_id: int, payment_method: str,
                         amount_paid: int, coupon_code: str | None = None,
                         external_payment_id: str | None = None) -> int | None:
    async with get_conn() as db:
        try:
            cur = await db.execute(
                "INSERT INTO orders "
                "(user_id, product_id, payment_method, amount_paid, coupon_code, external_payment_id) "
                "VALUES (?,?,?,?,?,?)",
                (user_id, product_id, payment_method, amount_paid, coupon_code, external_payment_id),
            )
        except Exception as error:
            if external_payment_id and "UNIQUE" in str(error).upper():
                return None
            raise
        await db.execute(
            "UPDATE users SET total_purchases = total_purchases + 1 WHERE user_id = ?", (user_id,)
        )
        await db.commit()
        return cur.lastrowid


async def has_purchased(user_id: int, product_id: int) -> bool:
    async with get_conn() as db:
        cur = await db.execute(
            "SELECT 1 FROM orders WHERE user_id=? AND product_id=? AND status='completed'",
            (user_id, product_id),
        )
        return (await cur.fetchone()) is not None


async def user_orders(user_id: int, limit: int = 20) -> list[dict]:
    async with get_conn() as db:
        cur = await db.execute(
            "SELECT o.*, p.name as product_name FROM orders o "
            "JOIN products p ON p.product_id = o.product_id "
            "WHERE o.user_id = ? ORDER BY o.order_id DESC LIMIT ?",
            (user_id, limit),
        )
        rows = await cur.fetchall()
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in rows]


# --------------------------------------------------------------- coupons ---
async def get_coupon(code: str) -> dict | None:
    async with get_conn() as db:
        cur = await db.execute("SELECT * FROM coupons WHERE code = ?", (code.upper(),))
        row = await cur.fetchone()
        if not row:
            return None
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))


async def create_coupon(code: str, discount_type: str, discount_value: int,
                         usage_limit: int = 0, expires_at: str | None = None) -> None:
    async with get_conn() as db:
        await db.execute(
            "INSERT INTO coupons (code, discount_type, discount_value, usage_limit, expires_at) "
            "VALUES (?,?,?,?,?)",
            (code.upper(), discount_type, discount_value, usage_limit, expires_at),
        )
        await db.commit()


async def redeem_coupon(code: str, user_id: int) -> None:
    async with get_conn() as db:
        await db.execute(
            "INSERT INTO coupon_usage (code, user_id) VALUES (?,?)", (code.upper(), user_id)
        )
        await db.execute(
            "UPDATE coupons SET used_count = used_count + 1 WHERE code = ?", (code.upper(),)
        )
        await db.commit()


async def coupon_already_used(code: str, user_id: int) -> bool:
    async with get_conn() as db:
        cur = await db.execute(
            "SELECT 1 FROM coupon_usage WHERE code=? AND user_id=?", (code.upper(), user_id)
        )
        return (await cur.fetchone()) is not None


def coupon_is_valid(coupon: dict) -> tuple[bool, str]:
    if not coupon or not coupon["is_active"]:
        return False, "কুপনটি খুঁজে পাওয়া যায়নি বা নিষ্ক্রিয়।"
    if coupon["usage_limit"] and coupon["used_count"] >= coupon["usage_limit"]:
        return False, "কুপনের ব্যবহার সীমা শেষ হয়ে গেছে।"
    if coupon["expires_at"]:
        try:
            exp = datetime.fromisoformat(coupon["expires_at"])
            if datetime.now(timezone.utc).replace(tzinfo=None) > exp:
                return False, "কুপনের মেয়াদ শেষ হয়ে গেছে।"
        except ValueError:
            pass
    return True, ""


# -------------------------------------------------------------- referral ---
async def mark_referral_rewarded(referred_id: int) -> int | None:
    """Called on a referred user's FIRST purchase. Returns referrer_id if rewarded now."""
    async with get_conn() as db:
        cur = await db.execute(
            "SELECT referrer_id, reward_given, status FROM referrals WHERE referred_id = ?",
            (referred_id,),
        )
        row = await cur.fetchone()
        if not row or row[1] or row[2] != "active":
            return None
        referrer_id = row[0]
        await db.execute(
            "UPDATE referrals SET reward_given = 1 WHERE referred_id = ?", (referred_id,)
        )
        await db.commit()
        return referrer_id


async def referral_stats(user_id: int) -> dict:
    async with get_conn() as db:
        cur = await db.execute(
            "SELECT COUNT(*), "
            "SUM(CASE WHEN status='active' THEN 1 ELSE 0 END), "
            "SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END), "
            "SUM(CASE WHEN status IN ('left','invalid') THEN 1 ELSE 0 END), "
            "SUM(reward_given) FROM referrals WHERE referrer_id = ?",
            (user_id,),
        )
        total, active, pending, invalid, rewarded = await cur.fetchone()
        return {
            "total": total or 0,
            "active": active or 0,
            "pending": pending or 0,
            "invalid": invalid or 0,
            "rewarded": rewarded or 0,
        }


async def referral_leaderboard(limit: int = 10) -> list[dict]:
    async with get_conn() as db:
        cur = await db.execute(
            "SELECT referrer_id, COUNT(*) as cnt FROM referrals WHERE status='active' "
            "GROUP BY referrer_id ORDER BY cnt DESC LIMIT ?",
            (limit,),
        )
        rows = await cur.fetchall()
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in rows]


async def set_referral_status(
    referred_id: int,
    status: str,
    reason: str | None = None,
) -> None:
    if status not in {"pending", "verified", "active", "left", "invalid"}:
        raise ValueError("Unsupported referral status")
    async with get_conn() as db:
        await db.execute(
            "UPDATE referrals SET status=?, verified_at=CASE WHEN ? IN ('verified','active') "
            "THEN COALESCE(verified_at, datetime('now')) ELSE verified_at END, "
            "last_checked_at=datetime('now'), invalid_reason=? WHERE referred_id=?",
            (status, status, reason, referred_id),
        )
        await db.commit()


async def referral_revalidation_targets() -> list[int]:
    async with get_conn() as db:
        cur = await db.execute(
            "SELECT referred_id FROM referrals WHERE status IN ('pending','verified','active','left')"
        )
        return [row[0] for row in await cur.fetchall()]


async def create_shared_link(
    owner_id: int,
    content_type: str,
    *,
    file_id: str | None = None,
    text_content: str | None = None,
    file_name: str | None = None,
    mime_type: str | None = None,
    expires_at: str | None = None,
    one_time: bool = False,
    max_views: int = 0,
    password_hash: str | None = None,
) -> str:
    token = secrets.token_urlsafe(9).replace("-", "").replace("_", "")[:12]
    async with get_conn() as db:
        await db.execute(
            "INSERT INTO shared_links "
            "(token, owner_id, content_type, file_id, text_content, file_name, mime_type, "
            "expires_at, one_time, max_views, password_hash) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                token,
                owner_id,
                content_type,
                file_id,
                text_content,
                file_name,
                mime_type,
                expires_at,
                int(one_time),
                max(0, max_views),
                password_hash,
            ),
        )
        await db.commit()
    return token


async def get_shared_link(token: str) -> dict | None:
    async with get_conn() as db:
        cur = await db.execute("SELECT * FROM shared_links WHERE token=?", (token,))
        row = await cur.fetchone()
        if not row:
            return None
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))


def shared_link_is_available(link: dict) -> tuple[bool, str]:
    if not link or not link.get("is_active"):
        return False, "This link is disabled."
    if link.get("expires_at"):
        try:
            if datetime.now(timezone.utc).replace(tzinfo=None) > datetime.fromisoformat(link["expires_at"]):
                return False, "This link has expired."
        except ValueError:
            return False, "This link has an invalid expiry."
    if link.get("max_views") and link["views"] >= link["max_views"]:
        return False, "This link reached its view limit."
    return True, ""


async def register_shared_link_view(token: str) -> dict | None:
    async with get_conn() as db:
        cur = await db.execute(
            "UPDATE shared_links SET views=views+1, last_accessed_at=datetime('now'), "
            "is_active=CASE WHEN one_time=1 OR (max_views > 0 AND views + 1 >= max_views) "
            "THEN 0 ELSE is_active END "
            "WHERE token=? AND is_active=1 AND (max_views=0 OR views < max_views)",
            (token,),
        )
        await db.commit()
        if not cur.rowcount:
            return None
    return await get_shared_link(token)


async def list_shared_links(owner_id: int, limit: int = 20) -> list[dict]:
    async with get_conn() as db:
        cur = await db.execute(
            "SELECT * FROM shared_links WHERE owner_id=? ORDER BY created_at DESC LIMIT ?",
            (owner_id, limit),
        )
        rows = await cur.fetchall()
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in rows]


async def set_shared_link_active(token: str, owner_id: int, active: bool) -> bool:
    async with get_conn() as db:
        cur = await db.execute(
            "UPDATE shared_links SET is_active=? WHERE token=? AND owner_id=?",
            (int(active), token, owner_id),
        )
        await db.commit()
        return cur.rowcount > 0


async def cleanup_shared_links() -> int:
    async with get_conn() as db:
        cur = await db.execute(
            "DELETE FROM shared_links WHERE expires_at IS NOT NULL "
            "AND expires_at < datetime('now')"
        )
        await db.commit()
        return cur.rowcount


async def cleanup_user_activity(days: int = 30) -> int:
    async with get_conn() as db:
        cur = await db.execute(
            "DELETE FROM user_activity WHERE created_at < datetime('now', ?)",
            (f"-{max(1, days)} days",),
        )
        await db.commit()
        return cur.rowcount


async def delete_shared_link(token: str, owner_id: int) -> bool:
    async with get_conn() as db:
        cur = await db.execute(
            "DELETE FROM shared_links WHERE token=? AND owner_id=?",
            (token, owner_id),
        )
        await db.commit()
        return cur.rowcount > 0


# ------------------------------------------------------------- analytics ---
async def sales_summary() -> dict:
    async with get_conn() as db:
        cur = await db.execute("SELECT COUNT(*), COALESCE(SUM(amount_paid),0) FROM orders WHERE payment_method='stars'")
        stars_orders, stars_revenue = await cur.fetchone()
        cur = await db.execute("SELECT COUNT(*), COALESCE(SUM(amount_paid),0) FROM orders WHERE payment_method='coin'")
        coin_orders, coin_revenue = await cur.fetchone()
        cur = await db.execute("SELECT COUNT(*) FROM users")
        (total_users,) = await cur.fetchone()
        cur = await db.execute("SELECT COUNT(*) FROM products WHERE is_active=1")
        (active_products,) = await cur.fetchone()
        cur = await db.execute("SELECT COUNT(*) FROM users WHERE is_banned=0")
        (active_users,) = await cur.fetchone()
        cur = await db.execute(
            "SELECT COUNT(*) FROM orders WHERE created_at >= datetime('now', '-1 day') "
            "AND status='completed'"
        )
        (orders_24h,) = await cur.fetchone()
        cur = await db.execute(
            "SELECT COUNT(*) FROM shared_links WHERE is_active=1"
        )
        (active_links,) = await cur.fetchone()
        return {
            "stars_orders": stars_orders, "stars_revenue": stars_revenue,
            "coin_orders": coin_orders, "coin_revenue": coin_revenue,
            "total_users": total_users, "active_users": active_users,
            "active_products": active_products, "orders_24h": orders_24h,
            "active_links": active_links,
        }


async def top_products(limit: int = 10) -> list[dict]:
    async with get_conn() as db:
        cur = await db.execute(
            "SELECT product_id, name, sales_count FROM products "
            "WHERE is_active=1 ORDER BY sales_count DESC, product_id DESC LIMIT ?",
            (limit,),
        )
        rows = await cur.fetchall()
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in rows]


async def refund_order(order_id: int, admin_id: int) -> dict | None:
    """Refund a completed coin order exactly once and write a compensating ledger entry."""
    async with get_conn() as db:
        cur = await db.execute(
            "SELECT order_id, user_id, product_id, payment_method, amount_paid, status "
            "FROM orders WHERE order_id=?",
            (order_id,),
        )
        row = await cur.fetchone()
        if not row or row[5] != "completed" or row[3] != "coin":
            return None
        await db.execute(
            "UPDATE orders SET status='refunded' WHERE order_id=? AND status='completed'",
            (order_id,),
        )
        await db.execute(
            "UPDATE products SET sales_count=MAX(0, sales_count-1) WHERE product_id=?",
            (row[2],),
        )
        cur = await db.execute("SELECT coin_balance FROM users WHERE user_id=?", (row[1],))
        balance_row = await cur.fetchone()
        new_balance = (balance_row[0] if balance_row else 0) + row[4]
        await db.execute("UPDATE users SET coin_balance=? WHERE user_id=?", (new_balance, row[1]))
        await db.execute(
            "INSERT INTO coin_transactions (user_id, amount, reason) VALUES (?,?,?)",
            (row[1], row[4], f"Refund for order #{order_id} by admin {admin_id}"),
        )
        await db.commit()
        return {
            "order_id": row[0],
            "user_id": row[1],
            "product_id": row[2],
            "amount_paid": row[4],
            "new_balance": new_balance,
        }


async def record_notification(user_id: int, kind: str, title: str, body: str) -> None:
    async with get_conn() as db:
        await db.execute(
            "INSERT INTO notifications (user_id, kind, title, body) VALUES (?,?,?,?)",
            (user_id, kind, title[:200], body[:4000]),
        )
        await db.commit()


# ------------------------------------------------------------- settings ----
async def get_setting(key: str, default: str = "") -> str:
    async with get_conn() as db:
        cur = await db.execute(
            "SELECT setting_value FROM app_settings WHERE setting_key = ?", (key,)
        )
        row = await cur.fetchone()
        return row[0] if row else default


async def set_setting(key: str, value: str) -> None:
    async with get_conn() as db:
        await db.execute(
            "INSERT INTO app_settings (setting_key, setting_value) VALUES (?,?) "
            "ON CONFLICT(setting_key) DO UPDATE SET setting_value=excluded.setting_value",
            (key, value),
        )
        await db.commit()


async def list_force_join_channels(active_only: bool = True) -> list[dict]:
    async with get_conn() as db:
        query = "SELECT * FROM force_join_channels"
        if active_only:
            query += " WHERE is_active=1"
        query += " ORDER BY title"
        cur = await db.execute(query)
        rows = await cur.fetchall()
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in rows]


async def add_force_join_channel(channel_id: int, title: str, invite_link: str) -> None:
    async with get_conn() as db:
        await db.execute(
            "INSERT INTO force_join_channels (channel_id, title, invite_link) "
            "VALUES (?,?,?) ON CONFLICT(channel_id) DO UPDATE SET "
            "title=excluded.title, invite_link=excluded.invite_link, is_active=1",
            (channel_id, title, invite_link),
        )
        await db.commit()


async def remove_force_join_channel(channel_id: int) -> None:
    async with get_conn() as db:
        await db.execute(
            "UPDATE force_join_channels SET is_active=0 WHERE channel_id=?", (channel_id,)
        )
        await db.commit()


async def search_products(query: str, limit: int = 20) -> list[dict]:
    term = f"%{query.strip()}%"
    async with get_conn() as db:
        cur = await db.execute(
            "SELECT * FROM products WHERE is_active=1 AND (name LIKE ? OR description LIKE ?) "
            "ORDER BY is_featured DESC, sales_count DESC, product_id DESC LIMIT ?",
            (term, term, limit),
        )
        rows = await cur.fetchall()
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in rows]


async def edit_product(product_id: int, field: str, value) -> bool:
    allowed = {"name", "description", "price_coin", "price_stars"}
    if field not in allowed:
        raise ValueError("Unsupported product field")
    async with get_conn() as db:
        cur = await db.execute(
            f"UPDATE products SET {field}=? WHERE product_id=?", (value, product_id)
        )
        await db.commit()
        return cur.rowcount > 0


async def set_product_featured(product_id: int, featured: bool) -> None:
    async with get_conn() as db:
        await db.execute(
            "UPDATE products SET is_featured=? WHERE product_id=?",
            (int(featured), product_id),
        )
        await db.commit()


async def delete_product(product_id: int) -> bool:
    """Soft-delete a product so existing order history remains intact."""
    async with get_conn() as db:
        cur = await db.execute(
            "UPDATE products SET is_active=0 WHERE product_id=?", (product_id,)
        )
        await db.commit()
        return cur.rowcount > 0


# ------------------------------------------------------------ wishlist -----
async def toggle_wishlist(user_id: int, product_id: int) -> bool:
    async with get_conn() as db:
        cur = await db.execute(
            "SELECT 1 FROM wishlists WHERE user_id=? AND product_id=?",
            (user_id, product_id),
        )
        exists = await cur.fetchone()
        if exists:
            await db.execute(
                "DELETE FROM wishlists WHERE user_id=? AND product_id=?",
                (user_id, product_id),
            )
            added = False
        else:
            await db.execute(
                "INSERT OR IGNORE INTO wishlists (user_id, product_id) VALUES (?,?)",
                (user_id, product_id),
            )
            added = True
        await db.commit()
        return added


async def user_wishlist(user_id: int) -> list[dict]:
    async with get_conn() as db:
        cur = await db.execute(
            "SELECT p.* FROM wishlists w JOIN products p ON p.product_id=w.product_id "
            "WHERE w.user_id=? AND p.is_active=1 ORDER BY w.created_at DESC",
            (user_id,),
        )
        rows = await cur.fetchall()
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in rows]


async def is_wishlisted(user_id: int, product_id: int) -> bool:
    async with get_conn() as db:
        cur = await db.execute(
            "SELECT 1 FROM wishlists WHERE user_id=? AND product_id=?",
            (user_id, product_id),
        )
        return (await cur.fetchone()) is not None


# -------------------------------------------------------------- reviews ----
async def add_review(user_id: int, product_id: int, rating: int, review: str) -> None:
    async with get_conn() as db:
        await db.execute(
            "INSERT INTO reviews (user_id, product_id, rating, review) VALUES (?,?,?,?) "
            "ON CONFLICT(user_id, product_id) DO UPDATE SET rating=excluded.rating, "
            "review=excluded.review, created_at=datetime('now'), is_visible=1",
            (user_id, product_id, rating, review),
        )
        await db.commit()


async def product_rating(product_id: int) -> dict:
    async with get_conn() as db:
        cur = await db.execute(
            "SELECT COUNT(*), COALESCE(AVG(rating),0) FROM reviews "
            "WHERE product_id=? AND is_visible=1",
            (product_id,),
        )
        count, average = await cur.fetchone()
        return {"count": count, "average": round(average, 1)}


async def product_reviews(product_id: int, limit: int = 5) -> list[dict]:
    async with get_conn() as db:
        cur = await db.execute(
            "SELECT r.*, u.username FROM reviews r LEFT JOIN users u ON u.user_id=r.user_id "
            "WHERE r.product_id=? AND r.is_visible=1 ORDER BY r.review_id DESC LIMIT ?",
            (product_id, limit),
        )
        rows = await cur.fetchall()
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in rows]


# ----------------------------------------------------------- daily bonus ----
async def claim_daily_checkin(user_id: int, reward_coins: int) -> int | None:
    today = datetime.now(timezone.utc).date().isoformat()
    async with get_conn() as db:
        cur = await db.execute(
            "SELECT 1 FROM daily_checkins WHERE user_id=? AND checkin_date=?",
            (user_id, today),
        )
        if await cur.fetchone():
            return None
        cur = await db.execute("SELECT coin_balance FROM users WHERE user_id=?", (user_id,))
        row = await cur.fetchone()
        if not row:
            return None
        new_balance = row[0] + reward_coins
        await db.execute(
            "INSERT INTO daily_checkins (user_id, checkin_date, reward_coins) VALUES (?,?,?)",
            (user_id, today, reward_coins),
        )
        await db.execute("UPDATE users SET coin_balance=? WHERE user_id=?", (new_balance, user_id))
        await db.execute(
            "INSERT INTO coin_transactions (user_id, amount, reason) VALUES (?,?,?)",
            (user_id, reward_coins, "Daily check-in bonus"),
        )
        await db.commit()
        return new_balance


# ------------------------------------------------------------- support -----
async def create_support_ticket(user_id: int, message: str) -> int:
    async with get_conn() as db:
        cur = await db.execute(
            "INSERT INTO support_tickets (user_id, message) VALUES (?,?)",
            (user_id, message),
        )
        await db.commit()
        return cur.lastrowid


async def open_support_tickets(limit: int = 30) -> list[dict]:
    async with get_conn() as db:
        cur = await db.execute(
            "SELECT t.*, u.username FROM support_tickets t "
            "LEFT JOIN users u ON u.user_id=t.user_id WHERE t.status='open' "
            "ORDER BY t.ticket_id ASC LIMIT ?",
            (limit,),
        )
        rows = await cur.fetchall()
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in rows]


async def get_support_ticket(ticket_id: int) -> dict | None:
    async with get_conn() as db:
        cur = await db.execute(
            "SELECT t.*, u.username FROM support_tickets t "
            "LEFT JOIN users u ON u.user_id=t.user_id WHERE t.ticket_id=?",
            (ticket_id,),
        )
        row = await cur.fetchone()
        if not row:
            return None
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))


async def close_support_ticket(ticket_id: int, admin_id: int, reply: str) -> dict | None:
    async with get_conn() as db:
        cur = await db.execute(
            "SELECT user_id FROM support_tickets WHERE ticket_id=? AND status='open'",
            (ticket_id,),
        )
        row = await cur.fetchone()
        if not row:
            return None
        await db.execute(
            "UPDATE support_tickets SET status='closed', admin_id=?, reply=?, "
            "updated_at=datetime('now') WHERE ticket_id=?",
            (admin_id, reply, ticket_id),
        )
        await db.commit()
        return {"ticket_id": ticket_id, "user_id": row[0], "reply": reply}


async def all_user_ids() -> list[int]:
    async with get_conn() as db:
        cur = await db.execute("SELECT user_id FROM users WHERE is_banned=0")
        return [row[0] for row in await cur.fetchall()]


async def user_report(user_id: int) -> dict | None:
    async with get_conn() as db:
        cur = await db.execute(
            "SELECT u.*, "
            "(SELECT COUNT(*) FROM orders o WHERE o.user_id=u.user_id AND o.status='completed') AS order_count, "
            "(SELECT COUNT(*) FROM shared_links l WHERE l.owner_id=u.user_id) AS link_count, "
            "(SELECT COUNT(*) FROM referrals r WHERE r.referrer_id=u.user_id AND r.status='active') AS active_referrals "
            "FROM users u WHERE u.user_id=?",
            (user_id,),
        )
        row = await cur.fetchone()
        if not row:
            return None
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))
