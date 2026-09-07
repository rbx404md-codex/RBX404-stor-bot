"""Small branded browser portal for opaque Telegram share links."""
import hashlib
import hmac
from html import escape
from io import BytesIO

from aiohttp import web

import config
from database.queries import (
    get_shared_link,
    register_shared_link_view,
    shared_link_is_available,
)


def _cookie_value(token: str) -> str:
    signature = hmac.new(
        config.LINK_SIGNING_SECRET.encode(),
        token.encode(),
        hashlib.sha256,
    ).hexdigest()
    return f"{token}.{signature}"


def _has_password_access(request: web.Request, token: str, link: dict) -> bool:
    if not link.get("password_hash"):
        return True
    value = request.cookies.get("rbx_link_access", "")
    expected = _cookie_value(token)
    return hmac.compare_digest(value, expected)


def _page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport"
content="width=device-width,initial-scale=1"><meta name="theme-color" content="#090d18">
<title>{escape(title)} · RBX404 Digital Store</title>
<style>
body{{margin:0;background:#090d18;color:#eef3ff;font-family:Inter,system-ui,sans-serif;
display:grid;place-items:center;min-height:100vh;padding:24px}}
main{{width:min(680px,100%);background:#111a2c;border:1px solid #273758;border-radius:24px;
padding:32px;box-shadow:0 24px 80px #0008}}h1{{margin:0 0 10px;color:#8ce7ff}}
.eyebrow{{color:#7d8ca8;letter-spacing:.16em;text-transform:uppercase;font-size:12px}}
.meta{{color:#aab9d4;margin:18px 0}}a,.button{{display:inline-block;background:#7c5cff;color:white;
padding:13px 18px;border-radius:12px;text-decoration:none;border:0;cursor:pointer;font-size:15px}}
input{{width:100%;box-sizing:border-box;padding:13px;border-radius:12px;border:1px solid #35496f;
background:#0b1220;color:white;margin:10px 0 14px}}.error{{color:#ff9aab}}
</style></head><body><main>{body}</main></body></html>"""


async def _resolve(request: web.Request) -> tuple[dict | None, str | None]:
    token = request.match_info["token"]
    link = await get_shared_link(token)
    if not link:
        return None, "This link does not exist."
    available, reason = shared_link_is_available(link)
    if not available:
        return None, reason
    if not _has_password_access(request, token, link):
        return None, None
    return link, None


async def link_page(request: web.Request) -> web.Response:
    token = request.match_info["token"]
    link, reason = await _resolve(request)
    if reason:
        return web.Response(
            text=_page("Unavailable", f"<div class='eyebrow'>⚡ RBX404</div><h1>Link unavailable</h1><p>{escape(reason)}</p>"),
            content_type="text/html",
            status=410,
        )
    if link is None:
        if request.method == "POST":
            form = await request.post()
            supplied = str(form.get("password", ""))
            original = await get_shared_link(token)
            supplied_hash = hashlib.sha256(supplied.encode()).hexdigest()
            if original and hmac.compare_digest(supplied_hash, original.get("password_hash") or ""):
                response = web.HTTPFound(f"/link/{token}")
                response.set_cookie("rbx_link_access", _cookie_value(token), httponly=True, samesite="Lax")
                raise response
        return web.Response(
            text=_page("Protected link", f"""<div class='eyebrow'>⚡ RBX404</div>
<h1>Protected link</h1><p>Enter the password to continue.</p>
<form method="post"><input name="password" type="password" placeholder="Password" required>
<button class="button" type="submit">Unlock</button></form>"""),
            content_type="text/html",
            status=401,
        )
    token = link["token"]
    public_download = f"/link/{token}/download"
    description = f"Shared {link['content_type']} via RBX404 Digital Store"
    body = (
        "<div class='eyebrow'>⚡ RBX404 DIGITAL STORE</div>"
        f"<h1>📦 Shared {escape(link['content_type'])}</h1>"
        f"<p class='meta'>👁 {link['views']} views · Created {escape(link['created_at'])}</p>"
        f"<a class='button' href='{public_download}'>Download / Open</a>"
        f"<p class='meta'><button class='button' type='button' "
        f"onclick='navigator.clipboard?.writeText(location.href)'>Share link</button></p>"
    )
    if link["content_type"] == "text":
        body += f"<pre style='white-space:pre-wrap;color:#cbd7ee;margin-top:28px'>{escape(link.get('text_content') or '')}</pre>"
    page = _page("Shared file", f"<meta name='description' content='{escape(description)}'>{body}")
    return web.Response(text=page, content_type="text/html")


async def download_link(request: web.Request) -> web.StreamResponse:
    link, reason = await _resolve(request)
    if reason or not link:
        return web.Response(text=reason or "Password required.", status=410 if reason else 401)
    link = await register_shared_link_view(link["token"])
    if not link:
        return web.Response(text="This link is no longer available.", status=410)
    if link["content_type"] == "text":
        return web.Response(text=link.get("text_content") or "", content_type="text/plain")
    bot = request.app["bot"]
    file_info = await bot.get_file(link["file_id"])
    buffer = BytesIO()
    await bot.download_file(file_info.file_path, buffer)
    return web.Response(
        body=buffer.getvalue(),
        content_type=link.get("mime_type") or "application/octet-stream",
        headers={
            "Content-Disposition": f'inline; filename="{(link.get("file_name") or "download").replace(chr(34), "")}"'
        },
    )


async def health(request: web.Request) -> web.Response:
    return web.json_response({"ok": True, "service": "rbx404-link-portal"})


async def portal_home(request: web.Request) -> web.Response:
    body = (
        "<div class='eyebrow'>⚡ RBX404 DIGITAL STORE</div>"
        "<h1>Your digital library, shared safely.</h1>"
        "<p class='meta'>Secure Telegram-powered delivery with expiring, password-protected share links.</p>"
        "<a class='button' href='https://t.me/RBX404_Digital_StoreBot'>Open Telegram Bot</a>"
    )
    return web.Response(text=_page("RBX404 Digital Store", body), content_type="text/html")


async def start_web_server(bot) -> web.AppRunner:
    app = web.Application()
    app["bot"] = bot
    app.router.add_get("/healthz", health)
    app.router.add_get("/", portal_home)
    app.router.add_get("/link/{token}", link_page)
    app.router.add_post("/link/{token}", link_page)
    app.router.add_get("/link/{token}/download", download_link)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", config.WEB_PORT)
    await site.start()
    return runner