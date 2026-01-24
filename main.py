import os
import asyncio
import threading
import logging
from fastapi import FastAPI, Request, HTTPException
import uvicorn

# Import các hàm và logic từ 2 file của mày
# Giả sử mày giữ nguyên file sepay_webhook.py và bot_shop.py
from sepay_webhook import process_payment, verify_sepay_auth
from bot_shop import main as start_bot_logic

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MAIN_ORCHESTRATOR")

app = FastAPI(title="Bot Shop & Sepay Orchestrator")

# 1. Route nhận Webhook từ Sepay
@app.post("/webhook/sepay")
async def sepay_webhook(request: Request):
    if not verify_sepay_auth(request):
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        payload = await request.json()
        # Chạy xử lý thanh toán trong Background để trả kết quả cho Sepay nhanh
        asyncio.create_task(process_payment(payload))
        logger.info("✅ Nhận tín hiệu từ Sepay, đang xử lý đơn hàng...")
        return {"ok": True, "message": "Webhook received"}
    except Exception as e:
        logger.error(f"❌ Lỗi xử lý Webhook: {e}")
        return {"ok": False, "error": str(e)}

@app.get("/")
async def health_check():
    return {"status": "Bot & Webhook are alive!", "kaomoji": "٩(͡๏̮͡๏)۶"}

# 2. Hàm chạy Bot Telegram (Polling)
def run_tele_bot():
    logger.info("🤖 Đang khởi động Bot Telegram...")
    # Vì bot_shop.py có hàm main() chứa app.run_polling(), ta gọi nó ở đây
    start_bot_logic()

# 3. Sự kiện khi Server khởi động
@app.on_event("startup")
async def on_startup():
    # Chạy Bot trong luồng riêng để không chặn FastAPI
    bot_thread = threading.Thread(target=run_tele_bot, daemon=True)
    bot_thread.start()
    logger.info("🚀 Hệ thống gộp đã sẵn sàng!")

if __name__ == "__main__":
    # Render cấp PORT qua biến môi trường, mặc định là 10000
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)