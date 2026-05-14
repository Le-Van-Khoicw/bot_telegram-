import asyncio
import logging
import os
import threading

import uvicorn
from fastapi import FastAPI, HTTPException, Request

from bot_shop import main as start_bot_logic
from sepay_webhook import process_payment, verify_sepay_auth

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MAIN_ORCHESTRATOR")

app = FastAPI()


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


@app.get("/")
async def health_check():
    return {"status": "Bot & Webhook are alive!"}


@app.head("/")
async def health_check_head():
    return None


def run_bot():
    try:
        logger.info("Starting Telegram bot polling in background thread...")
        start_bot_logic()
    except Exception:
        logger.exception("Telegram bot crashed")


if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

    port = int(os.environ.get("PORT", 10000))
    logger.info("Starting FastAPI webhook server on port %s...", port)
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
