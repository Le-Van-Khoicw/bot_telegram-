import asyncio
from collections import OrderedDict
import logging
import os
import threading
import time

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from telegram import Update

from admin_dashboard import register_admin_routes
from bot_shop import build_application, main as start_bot_logic, setup_bot_commands
from sepay_webhook import process_payment, set_telegram_bot, verify_sepay_auth

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MAIN_ORCHESTRATOR")

app = FastAPI()
telegram_app = None
PROCESSED_UPDATE_IDS = OrderedDict()
register_admin_routes(app)


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


async def handle_sepay_webhook(request: Request):
    if not verify_sepay_auth(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        payload = await request.json()
        asyncio.create_task(process_payment(payload))
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/webhook/sepay")
async def sepay_webhook(request: Request):
    return await handle_sepay_webhook(request)


@app.post("/")
async def sepay_root_fallback(request: Request):
    return await handle_sepay_webhook(request)


@app.post(telegram_webhook_path())
async def telegram_webhook(request: Request):
    if telegram_app is None:
        raise HTTPException(status_code=503, detail="Telegram app is not ready")
    payload = await request.json()
    update_id = payload.get("update_id")
    now = time.time()
    for old_id, seen_at in list(PROCESSED_UPDATE_IDS.items()):
        if now - seen_at > 600 or len(PROCESSED_UPDATE_IDS) > 1000:
            PROCESSED_UPDATE_IDS.pop(old_id, None)
        else:
            break
    if update_id is not None:
        if update_id in PROCESSED_UPDATE_IDS:
            logger.info("Skip duplicate Telegram update_id=%s", update_id)
            return {"ok": True, "duplicate": True}
        PROCESSED_UPDATE_IDS[update_id] = now
    update = Update.de_json(payload, telegram_app.bot)
    await telegram_app.process_update(update)
    return {"ok": True}


@app.get("/")
async def health_check():
    return {"status": "Bot & Webhook are alive!", "telegram_mode": "webhook" if telegram_app else "polling"}


@app.get("/ping")
async def ping():
    return "ok"


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
    await setup_bot_commands(telegram_app)
    set_telegram_bot(telegram_app.bot)
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
