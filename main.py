import asyncio
import logging
import os
import threading

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from telegram import Update

from bot_shop import build_application, get_admin_snapshot, main as start_bot_logic
from sepay_webhook import process_payment, verify_sepay_auth

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MAIN_ORCHESTRATOR")

app = FastAPI()
telegram_app = None


ADMIN_HTML = """<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Bot Admin</title>
  <style>
    :root { color-scheme: dark; font-family: Arial, sans-serif; }
    body { margin: 0; background: #111; color: #eee; }
    header { display: flex; gap: 12px; align-items: center; justify-content: space-between; padding: 16px 20px; background: #1d1d1d; border-bottom: 1px solid #333; }
    input, button { border: 1px solid #444; border-radius: 6px; padding: 9px 10px; background: #191919; color: #eee; }
    button { cursor: pointer; background: #2b6b3f; border-color: #3a8b54; font-weight: 700; }
    main { padding: 18px; max-width: 1280px; margin: auto; }
    .grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }
    .card { background: #1b1b1b; border: 1px solid #333; border-radius: 8px; padding: 14px; }
    .label { color: #aaa; font-size: 12px; text-transform: uppercase; }
    .value { font-size: 24px; margin-top: 8px; font-weight: 700; }
    table { width: 100%; border-collapse: collapse; margin-top: 12px; background: #171717; }
    th, td { border-bottom: 1px solid #2c2c2c; padding: 8px; text-align: left; font-size: 13px; vertical-align: top; }
    th { position: sticky; top: 0; background: #222; z-index: 1; }
    .section { margin-top: 18px; }
    .scroll { max-height: 520px; overflow: auto; border: 1px solid #333; border-radius: 8px; }
    .pill { display: inline-block; padding: 3px 7px; border-radius: 999px; background: #333; }
    .DELIVERED, .PAID { background: #184f2b; }
    .PENDING { background: #5b4a18; }
    .CANCELLED, .EXPIRED { background: #5b1e1e; }
    @media (max-width: 800px) { .grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } header { flex-direction: column; align-items: stretch; } }
  </style>
</head>
<body>
  <header>
    <h2>Khoi Van Store Admin</h2>
    <div>
      <input id="key" placeholder="ADMIN_PASSWORD" type="password" />
      <button onclick="loadData()">Refresh</button>
    </div>
  </header>
  <main>
    <div id="message">Nhap ADMIN_PASSWORD roi bam Refresh.</div>
    <div class="grid section" id="summary"></div>
    <div class="section">
      <h3>San pham dang ban</h3>
      <div class="scroll"><table id="products"></table></div>
    </div>
    <div class="section">
      <h3>Don hang moi nhat</h3>
      <div class="scroll"><table id="orders"></table></div>
    </div>
  </main>
  <script>
    const saved = localStorage.getItem("admin_key") || "";
    document.getElementById("key").value = saved;
    const fmt = n => Number(n || 0).toLocaleString("vi-VN");
    const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
    async function loadData() {
      const key = document.getElementById("key").value.trim();
      localStorage.setItem("admin_key", key);
      const msg = document.getElementById("message");
      msg.textContent = "Dang tai...";
      const res = await fetch(`/admin/api/snapshot?key=${encodeURIComponent(key)}`);
      if (!res.ok) {
        msg.textContent = await res.text();
        return;
      }
      const data = await res.json();
      msg.textContent = `Cap nhat: ${data.generated_at} (${data.timezone})`;
      const counts = data.summary.status_counts || {};
      document.getElementById("summary").innerHTML = [
        ["Tong don", data.summary.orders],
        ["Doanh thu", fmt(data.summary.revenue) + " d"],
        ["Pending", counts.PENDING || 0],
        ["Delivered", counts.DELIVERED || 0],
      ].map(([a,b]) => `<div class="card"><div class="label">${a}</div><div class="value">${b}</div></div>`).join("");
      document.getElementById("products").innerHTML = `<tr><th>Ten</th><th>Stock</th><th>Gia</th><th>Con</th></tr>` +
        data.products.map(p => `<tr><td>${esc(p.name)}</td><td>${esc(p.stock_code)}</td><td>${fmt(p.price)}</td><td>${p.ready}</td></tr>`).join("");
      document.getElementById("orders").innerHTML = `<tr><th>Order</th><th>User</th><th>SP</th><th>SL</th><th>Total</th><th>Status</th><th>Created</th><th>Paid</th><th>Delivered</th></tr>` +
        data.orders.map(o => `<tr><td>${esc(o.order_id)}</td><td>${esc(o.user_id)}</td><td>${esc(o.stock_code)}</td><td>${esc(o.qty)}</td><td>${fmt(o.total)}</td><td><span class="pill ${esc(o.status)}">${esc(o.status)}</span></td><td>${esc(o.created_at)}</td><td>${esc(o.paid_at)}</td><td>${esc(o.delivered_at)}</td></tr>`).join("");
    }
  </script>
</body>
</html>"""


def public_base_url() -> str:
    raw = (
        os.environ.get("TELEGRAM_WEBHOOK_URL")
        or os.environ.get("WEBHOOK_URL")
        or os.environ.get("RENDER_EXTERNAL_URL")
        or os.environ.get("PUBLIC_URL")
        or ""
    ).strip()
    return raw.rstrip("/")


def telegram_webhook_path() -> str:
    return "/webhook/telegram"


@app.post("/webhook/sepay")
async def sepay_webhook(request: Request):
    if not verify_sepay_auth(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        payload = await request.json()
        asyncio.create_task(process_payment(payload))
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post(telegram_webhook_path())
async def telegram_webhook(request: Request):
    if telegram_app is None:
        raise HTTPException(status_code=503, detail="Telegram app is not ready")
    payload = await request.json()
    update = Update.de_json(payload, telegram_app.bot)
    await telegram_app.process_update(update)
    return {"ok": True}


@app.get("/")
async def health_check():
    return {"status": "Bot & Webhook are alive!", "telegram_mode": "webhook" if telegram_app else "polling"}


@app.get("/ping")
async def ping():
    return "ok"


def require_admin(request: Request) -> None:
    expected = os.environ.get("ADMIN_PASSWORD", "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="Set ADMIN_PASSWORD in Render Environment first.")
    provided = (request.query_params.get("key") or request.headers.get("x-admin-key") or "").strip()
    if provided != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/admin", response_class=HTMLResponse)
async def admin_page():
    return ADMIN_HTML


@app.get("/admin/api/snapshot")
async def admin_snapshot(request: Request, limit: int = 100):
    require_admin(request)
    return await asyncio.to_thread(get_admin_snapshot, limit)


@app.head("/")
async def health_check_head():
    return None


def run_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        logger.info("Starting Telegram bot polling in background thread...")
        start_bot_logic()
    except Exception:
        logger.exception("Telegram bot crashed")
    finally:
        loop.close()


@app.on_event("startup")
async def startup_telegram_webhook():
    global telegram_app
    base_url = public_base_url()
    if not base_url:
        logger.info("No public URL configured; Telegram bot will use polling fallback.")
        return

    webhook_url = f"{base_url}{telegram_webhook_path()}"
    telegram_app = build_application()
    await telegram_app.initialize()
    await telegram_app.bot.set_webhook(webhook_url, drop_pending_updates=True)
    await telegram_app.start()
    logger.info("Telegram webhook is active: %s", webhook_url)


@app.on_event("shutdown")
async def shutdown_telegram_webhook():
    global telegram_app
    if telegram_app is None:
        return
    await telegram_app.stop()
    await telegram_app.shutdown()
    telegram_app = None


if __name__ == "__main__":
    if not public_base_url():
        bot_thread = threading.Thread(target=run_bot, daemon=True)
        bot_thread.start()

    port = int(os.environ.get("PORT", 10000))
    logger.info("Starting FastAPI webhook server on port %s...", port)
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
