# 🚀 START HERE - Test Local Trước Khi Deploy

## ⚡ Quick Start (5 phút)

### Bước 1: Chạy tất cả tests

```bash
cd d:\TOOl_FARM\bottele
python run_all_tests.py
```

**Kết quả mong đợi:**
```
✓ PASS - Test 1: Integration Test
✓ PASS - Test 2: Bot Commands
✓ PASS - Test 3: Google Sheets
✓ PASS - Test 4: Selenium

Kết quả: 4 passed, 0 failed, 0 skipped / 4 total

🎉 TẤT CẢ TESTS ĐỀU PASS!
```

### Bước 2: Thêm thẻ test

```bash
python add_test_cards.py add
```

### Bước 3: Patch bot_shop.py

```bash
python bot_shop_payment_patch.py
```

### Bước 4: Chạy bot

```bash
python main.py
```

### Bước 5: Test trên Telegram

1. `/start`
2. Bấm "🛍 Sản phẩm"
3. Chọn product
4. Bấm "Mua"
5. Xem kết quả!

---

## 📁 Files Test

| File | Mô tả | Chạy |
|------|-------|------|
| `run_all_tests.py` | Chạy tất cả tests | `python run_all_tests.py` |
| `test_integration.py` | Test tích hợp | `python test_integration.py` |
| `test_bot_commands.py` | Test commands | `python test_bot_commands.py` |
| `test_sheets.py` | Test Google Sheets | `python test_sheets.py` |
| `test_selenium.py` | Test browser | `python test_selenium.py` |
| `add_test_cards.py` | Quản lý thẻ | `python add_test_cards.py add\|list` |

---

## 🧪 Test Từng Phần

### Test 1: Integration (Nhanh - 5s)

```bash
python test_integration.py
```

Kiểm tra:
- ✅ Imports
- ✅ Database
- ✅ Payment service
- ✅ Product model
- ✅ Env config
- ✅ File structure

### Test 2: Bot Commands (Nhanh - 5s)

```bash
python test_bot_commands.py
```

Kiểm tra:
- ✅ IntegratedPaymentService
- ✅ Get payment stats
- ✅ Get cards
- ✅ ProductWithPayment model
- ✅ Database operations

### Test 3: Google Sheets (Trung bình - 10s)

```bash
python test_sheets.py
```

Kiểm tra:
- ✅ Connection
- ✅ Load products
- ✅ Load stock
- ✅ Payment fields

### Test 4: Selenium (Chậm - 30s)

```bash
python test_selenium.py
```

Kiểm tra:
- ✅ Browser automation
- ✅ Navigate
- ✅ Screenshots
- ✅ Close driver

**Note:** Browser sẽ mở, bạn sẽ thấy Chrome automation

---

## 🔧 Nếu Test Fail

### Test Integration fail:
```bash
# Check dependencies
pip install -r requirements.txt
cd ..\pay_kiro
pip install -r requirements.txt
```

### Test Bot Commands fail:
```bash
# Thêm thẻ test
python add_test_cards.py add
```

### Test Google Sheets fail:
```bash
# Check .env
# Check service_account.json
# Check GSHEET_ID
```

### Test Selenium fail:
```bash
# Update webdriver-manager
pip install --upgrade webdriver-manager

# Check Chrome installed
chrome --version
```

---

## 📊 Checklist Trước Khi Deploy

### Local Tests:
- [ ] `run_all_tests.py` - 4/4 pass
- [ ] Đã thêm thẻ test
- [ ] Đã patch bot_shop.py
- [ ] Bot chạy OK local
- [ ] Test mua hàng OK

### Google Sheets:
- [ ] Đã thêm cột payment vào PRODUCTS
- [ ] Có ít nhất 1 product test
- [ ] Có items trong POOL

### Environment:
- [ ] `.env` configured
- [ ] `service_account.json` exists
- [ ] Chrome installed
- [ ] Dependencies installed

### Ready to Deploy:
- [ ] Set `PAYMENT_HEADLESS=True`
- [ ] Backup database
- [ ] Push code to Git
- [ ] Deploy to Render

---

## 🎯 Test Flow Mua Hàng

### Flow 1: Product KHÔNG cần payment

1. Chạy bot: `python main.py`
2. Telegram: `/start` → "🛍 Sản phẩm"
3. Chọn product có `requires_payment = no`
4. Bấm "Mua" → Nhập số lượng
5. **Kết quả:** Bot tạo QR code

### Flow 2: Product CẦN payment (⭐ Mới)

1. Chạy bot: `python main.py`
2. Telegram: `/start` → "🛍 Sản phẩm"
3. Chọn product có `requires_payment = yes`
4. Bấm "Mua" → Nhập số lượng
5. **Kết quả:** Bot tự động thanh toán

**Xem browser (nếu PAYMENT_HEADLESS=False):**
- Browser mở
- Navigate đến payment URL
- Điền thông tin thẻ
- Submit
- Giao hàng

---

## 💡 Tips

1. **Test từng bước** - Đừng skip tests
2. **Check logs** - Xem `payment_automation.log`
3. **Set headless=False** - Để debug
4. **Backup database** - Trước mỗi test
5. **Use mock URLs** - Test với httpbin.org

---

## 📞 Support

### Logs:
- `payment_automation.log` - Payment logs
- `screenshots/` - Screenshots
- Console output - Bot logs

### Common Issues:

**"No active cards"**
→ `python add_test_cards.py add`

**"Google Sheets connection failed"**
→ Check `.env` và `service_account.json`

**"ChromeDriver not found"**
→ `pip install --upgrade webdriver-manager`

**"Payment timeout"**
→ Tăng `PAYMENT_TIMEOUT` trong `.env`

---

## 🚀 Sau Khi Test OK

### 1. Cleanup:
```bash
# Xóa test data (optional)
# Giữ lại thẻ test
```

### 2. Chuẩn bị deploy:
- Set `PAYMENT_HEADLESS=True`
- Update products thật
- Thêm thẻ thật (nếu có)

### 3. Deploy:
- Push to Git
- Deploy to Render
- Set env variables
- Test production

---

## 📚 Documentation

| File | Purpose |
|------|---------|
| `START_HERE.md` | File này - Quick start |
| `LOCAL_TEST_GUIDE.md` | Hướng dẫn test chi tiết |
| `QUICK_START_PAYMENT.md` | Setup payment |
| `INTEGRATION_GUIDE.md` | Integration guide |
| `SUMMARY.md` | Tổng kết |

**Đọc theo thứ tự:**
1. `START_HERE.md` ← Bạn đang đọc
2. `LOCAL_TEST_GUIDE.md` - Nếu cần chi tiết
3. `QUICK_START_PAYMENT.md` - Setup payment
4. `INTEGRATION_GUIDE.md` - Deep dive

---

## ✅ Ready?

Chạy ngay:

```bash
python run_all_tests.py
```

Nếu 4/4 tests pass → Bạn đã sẵn sàng! 🎉

---

**Good luck! 🚀**
