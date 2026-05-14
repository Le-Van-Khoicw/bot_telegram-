# 🚀 Quick Start: Tích hợp Auto Payment

## 📦 Files đã tạo

1. ✅ `integrated_payment.py` - Core payment integration
2. ✅ `INTEGRATION_GUIDE.md` - Hướng dẫn chi tiết
3. ✅ `add_test_cards.py` - Script thêm thẻ test
4. ✅ `bot_shop_payment_patch.py` - Auto patch bot_shop.py
5. ✅ `QUICK_START_PAYMENT.md` - File này

---

## ⚡ Setup nhanh (5 phút)

### Bước 1: Thêm thẻ test

```bash
cd d:\TOOl_FARM\bottele
python add_test_cards.py add
```

**Output:**
```
============================================================
THÊM THẺ TEST VÀO DATABASE
============================================================

✓ [1/3] Added card ID: 1
   Số thẻ: ****8586
   Chủ thẻ: NGUYEN VAN A
   Priority: 1

✓ [2/3] Added card ID: 2
   Số thẻ: ****1096
   Chủ thẻ: TRAN THI B
   Priority: 2

✓ [3/3] Added card ID: 3
   Số thẻ: ****1111
   Chủ thẻ: LE VAN C
   Priority: 3

============================================================
✅ HOÀN TẤT! Đã thêm 3/3 thẻ
============================================================
```

### Bước 2: Update Google Sheets

Thêm các cột sau vào sheet **PRODUCTS**:

| Column Name | Example Value |
|-------------|---------------|
| `requires_payment` | `yes` hoặc `no` |
| `payment_url` | `https://kiro.ai/payment` |
| `payment_provider` | `custom` |
| `account_email` | `user@example.com` |
| `account_password` | `password123` |

**Ví dụ row:**

| product_id | name | price | stock_code | requires_payment | payment_url | account_email |
|------------|------|-------|------------|------------------|-------------|---------------|
| KIRO_PRO | Kiro Pro 1M | 350000 | KIRO_ACC | yes | https://kiro.ai/payment | test@example.com |

### Bước 3: Patch bot_shop.py (Tự động)

```bash
python bot_shop_payment_patch.py
```

**Output:**
```
============================================================
BOT_SHOP.PY AUTO PAYMENT PATCH
============================================================

📦 Đang backup file...
✓ Đã backup: bot_shop.py.backup

🔧 Đang apply patches...

✓ Đã thêm import section
✓ Đã update load_products()
✓ Đã thêm payment handlers
✓ Đã thêm command handlers

💾 Đang lưu file...
✓ Đã lưu file

============================================================
✅ PATCH HOÀN TẤT!
============================================================
```

### Bước 4: Cấu hình .env

Thêm vào file `.env`:

```env
# Auto Payment Config
PAYMENT_HEADLESS=True
MAX_RETRY_CARDS=3
PAYMENT_TIMEOUT=60
```

### Bước 5: Chạy bot

```bash
python main.py
```

---

## 🧪 Test

### Test 1: Kiểm tra thẻ

Trên Telegram (với admin account):

```
/list_cards
```

**Kết quả:**
```
💳 DANH SÁCH THẺ (3 thẻ)

🆔 ID: 1
💳 Số: ****8586
👤 Tên: NGUYEN VAN A
✅ Thành công: 0 | ❌ Thất bại: 0
⭐ Priority: 1
──────────────────────────────
...
```

### Test 2: Mua product có payment

1. `/start`
2. Bấm "🛍 Sản phẩm"
3. Chọn product có `requires_payment = yes`
4. Bấm "Mua"

**Bot sẽ:**
```
⏳ ĐANG XỬ LÝ...

🧾 Mã đơn: ORD20260510120000ABCD
📦 SP: Kiro Pro 1M
💰 Giá: 350.000 đ

🔄 Đang tự động thanh toán...
⏱ Vui lòng đợi 30-60 giây...
```

Sau đó:
```
✅ THANH TOÁN THÀNH CÔNG

🧾 Mã đơn: ORD20260510120000ABCD
📦 SP: Kiro Pro 1M
💰 Giá: 350.000 đ

💳 Thẻ: ****8586

🎁 Đang giao hàng...
```

### Test 3: Xem thống kê

```
/payment_stats
```

**Kết quả:**
```
📊 THỐNG KÊ THANH TOÁN

💳 Thẻ active: 3
✅ Thành công: 1
❌ Thất bại: 0
📈 Tỷ lệ: 100.0%
```

---

## 🎯 Flow hoàn chỉnh

### Product KHÔNG cần payment (flow cũ):
```
User mua → Reserve items → Tạo QR → User CK → Webhook → Giao hàng
```

### Product CẦN payment (flow mới):
```
User mua → Reserve items → Auto thanh toán → Giao hàng ngay
                                ↓
                          (Dùng thẻ trong DB)
```

---

## 📊 So sánh

| Feature | Trước | Sau |
|---------|-------|-----|
| Thời gian giao hàng | 5-30 phút | 30-60 giây |
| Cần admin | ✅ Có | ❌ Không |
| Tự động 100% | ❌ Không | ✅ Có |
| Retry khi lỗi | ❌ Không | ✅ Có (3 thẻ) |
| Tracking | ⚠️ Thủ công | ✅ Tự động |

---

## 🔧 Commands mới

### User commands:
- Không có thay đổi (flow tự động)

### Admin commands:
- `/payment_stats` - Xem thống kê thanh toán
- `/list_cards` - Xem danh sách thẻ

---

## 🐛 Troubleshooting

### Lỗi: "No active cards available"

**Nguyên nhân:** Chưa có thẻ trong database

**Giải pháp:**
```bash
python add_test_cards.py add
```

### Lỗi: "Failed to navigate to payment page"

**Nguyên nhân:** 
- `payment_url` sai
- ChromeDriver chưa cài

**Giải pháp:**
1. Kiểm tra `payment_url` trong Google Sheets
2. Set `PAYMENT_HEADLESS=False` để xem browser
3. Cài ChromeDriver:
   ```bash
   pip install webdriver-manager
   ```

### Lỗi: "All cards failed"

**Nguyên nhân:**
- Thẻ không valid
- Selector trong code sai

**Giải pháp:**
1. Kiểm tra thẻ có đúng không
2. Xem log: `payment_automation.log`
3. Xem screenshots: `screenshots/`

### Payment chậm

**Giải pháp:**
- Giảm `PAYMENT_TIMEOUT` trong `.env`
- Tăng `MAX_RETRY_CARDS`
- Set `PAYMENT_HEADLESS=True`

---

## 📁 Cấu trúc thư mục

```
TOOl_FARM/
├── bottele/
│   ├── bot_shop.py                    # ✅ Đã patch
│   ├── bot_shop.py.backup             # ✅ Backup
│   ├── integrated_payment.py          # ✅ Mới
│   ├── add_test_cards.py              # ✅ Mới
│   ├── bot_shop_payment_patch.py      # ✅ Mới
│   ├── INTEGRATION_GUIDE.md           # ✅ Mới
│   ├── QUICK_START_PAYMENT.md         # ✅ File này
│   └── ...
└── pay_kiro/
    ├── database.py
    ├── payment_automation.py
    ├── cards.db                        # ✅ Có thẻ test
    └── ...
```

---

## ✅ Checklist

- [ ] Đã chạy `add_test_cards.py add`
- [ ] Đã update Google Sheets (thêm cột payment)
- [ ] Đã chạy `bot_shop_payment_patch.py`
- [ ] Đã thêm config vào `.env`
- [ ] Đã test `/list_cards`
- [ ] Đã test mua product có payment
- [ ] Đã test `/payment_stats`

---

## 🎓 Tài liệu

- **Chi tiết:** `INTEGRATION_GUIDE.md`
- **Code:** `integrated_payment.py`
- **Patch:** `bot_shop_payment_patch.py`

---

## 💡 Tips

1. **Test với product giá rẻ trước** (10.000đ)
2. **Set PAYMENT_HEADLESS=False** lần đầu để xem browser
3. **Check log** trong `payment_automation.log`
4. **Backup database** trước khi test: `copy cards.db cards.db.backup`

---

## 🚀 Next Steps

Sau khi test thành công:

1. Thêm thẻ thật vào database
2. Update products thật trong Google Sheets
3. Set `PAYMENT_HEADLESS=True`
4. Deploy lên server
5. Monitor logs và stats

---

## 📞 Support

Nếu gặp vấn đề:

1. Check log: `payment_automation.log`
2. Check screenshots: `screenshots/`
3. Check database: `cards.db`
4. Restore backup: `copy bot_shop.py.backup bot_shop.py`

Hoặc hỏi tôi! 😊

---

**Chúc bạn thành công! 🎉**
