import os
import threading
import logging
import uvicorn
from fastapi import FastAPI, Request, HTTPException
import asyncio

# Import từ file của mày
from sepay_webhook import process_payment, verify_sepay_auth
from bot_shop import main as start_bot_logic

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
    return {"status": "Bot & Webhook are alive!", "kaomoji": "٩(͡๏̮͡๏)۶"}

def run_fastapi():
    # Cho FastAPI chạy ở luồng phụ
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")

if __name__ == "__main__":
    # 1. Bật FastAPI ở luồng phụ trước
    api_thread = threading.Thread(target=run_fastapi, daemon=True)
    api_thread.start()

    logger.info("🚀 Webhook (FastAPI) đang chạy ở luồng phụ...")

    # 2. Quan trọng: Chỉnh lại bot_shop.py
    # Mày phải đảm bảo trong bot_shop.py, hàm app.run_polling()
    # được gọi với tham số stop_signals=False
    logger.info("🤖 Đang khởi động Bot Telegram ở luồng chính...")
    start_bot_logic()