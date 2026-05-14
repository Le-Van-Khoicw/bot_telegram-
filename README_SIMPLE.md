# 🤖 Shop Bot + Auto Payment

## 🎯 Tính năng

✅ Bot Telegram bán hàng tự động  
✅ Tích hợp Google Sheets  
✅ Webhook SePay tự động giao hàng  
✅ **Auto Payment** - Tự động thanh toán khi mua hàng  

---

## 📁 Files quan trọng

### Code chính:
- **`main.py`** - Chạy bot
- **`bot_shop.py`** - Bot Telegram
- **`sepay_webhook.py`** - Webhook SePay
- **`integrated_payment.py`** - Auto payment ⭐ MỚI

### Scripts:
- **`add_test_cards.py`** - Thêm thẻ test
- **`run_all_tests.py`** - Chạy tests
- **`bot_shop_payment_patch.py`** - Patch bot

### Docs:
- **`START_HERE.md`** - Bắt đầu từ đây ⭐
- **`QUICK_START_PAYMENT.md`** - Quick start
- **`SUMMARY.md`** - Tổng kết

---

## ⚡ Quick Start (3 bước)

### 1. Test
```bash
python run_all_tests.py
```

### 2. Thêm thẻ
```bash
python add_test_cards.py add
```

### 3. Chạy bot
```bash
python main.py
```

---

## 🔧 Cấu hình

File `.env`:
```env
# Bot
BOT_TOKEN=your_token

# Google Sheets
GSHEET_ID=your_sheet_id
GSVC_JSON=service_account.json

# Auto Payment (MỚI)
PAYMENT_HEADLESS=False
MAX_RETRY_CARDS=3
```

---

## 📊 Flow

### Mua hàng thường:
```
User mua → QR code → User CK → Webhook → Giao hàng
```

### Mua hàng có payment (MỚI):
```
User mua → Auto thanh toán → Giao hàng ngay (30s)
```

---

## 🧪 Test

```bash
# Test tất cả
python run_all_tests.py

# Test riêng
python test_integration.py
python test_sheets.py
python test_selenium.py
```

---

## 📚 Docs

| File | Mô tả |
|------|-------|
| `START_HERE.md` | Bắt đầu (5 phút) |
| `QUICK_START_PAYMENT.md` | Setup payment (10 phút) |
| `INTEGRATION_GUIDE.md` | Chi tiết (30 phút) |
| `SUMMARY.md` | Tổng kết (5 phút) |

---

## 🎯 Tổ chức lại (Optional)

Nếu muốn tổ chức files gọn gàng hơn:

```bash
python organize_files.py
```

Sẽ tạo cấu trúc:
```
bottele/
├── payment/    # Auto payment
├── scripts/    # Helper scripts
├── tests/      # Tests
├── docs/       # Documentation
└── main.py     # Entry point
```

---

## 💡 Tips

1. **Đọc START_HERE.md trước** - Hiểu tổng quan
2. **Test local trước** - Trước khi deploy
3. **Check logs** - Khi có lỗi
4. **Backup database** - Trước mỗi test

---

## 📞 Support

- **Logs:** `payment_automation.log`
- **Screenshots:** `screenshots/`
- **Database:** `cards.db`

---

**Made with ❤️ by Kiro AI**
