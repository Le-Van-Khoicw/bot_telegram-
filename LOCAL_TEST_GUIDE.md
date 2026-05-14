# 🧪 Hướng dẫn Test Local (Trước khi lên Render)

## 📋 Checklist Test

- [ ] Test 1: Kiểm tra môi trường
- [ ] Test 2: Test database & thẻ
- [ ] Test 3: Test Google Sheets connection
- [ ] Test 4: Test Selenium (browser automation)
- [ ] Test 5: Test bot commands
- [ ] Test 6: Test flow mua hàng (không payment)
- [ ] Test 7: Test flow mua hàng (có payment)
- [ ] Test 8: Test webhook SePay

---

## 🛠️ Setup môi trường Local

### 1. Cài đặt dependencies

```bash
cd d:\TOOl_FARM\bottele
pip install -r requirements.txt

cd ..\pay_kiro
pip install -r requirements.txt
```

### 2. Kiểm tra Chrome & ChromeDriver

```bash
# Check Chrome version
chrome --version

# ChromeDriver sẽ tự động download khi chạy lần đầu
```

### 3. Cấu hình .env

File `.env` trong `bottele/`:

```env
# Bot Config
BOT_TOKEN=your_bot_token_here
SHOP_NAME=Test Shop

# Google Sheets
GSHEET_ID=your_sheet_id
GSVC_JSON=service_account.json

# Tabs
ORDERS_TAB=ORDERS
PRODUCTS_TAB=PRODUCTS
POOL_TAB=POOL
RESERVATIONS_TAB=RESERVATIONS
USERS_TAB=USERS

# Admin
ADMIN_IDS=your_telegram_id

# Payment (SePay)
BANK_CODE=BIDV
BANK_NUMBER=8867625524
BANK_OWNER=NGUYEN VAN MINH

# SePay Webhook
SEPAY_API_KEY=your_sepay_key

# ✅ AUTO PAYMENT CONFIG
PAYMENT_HEADLESS=False  # Set False để xem browser khi test
MAX_RETRY_CARDS=3
PAYMENT_TIMEOUT=60

# Order TTL
ORDER_TTL_SECONDS=600
```

---

## 🧪 Test 1: Kiểm tra môi trường

```bash
cd d:\TOOl_FARM\bottele
python test_integration.py
```

**Kết quả mong đợi:**
```
✓ PASS - Imports
✓ PASS - Database
✓ PASS - Payment Service
✓ PASS - Product Model
✓ PASS - Env Config
✓ PASS - File Structure
✓ PASS - Async Payment

Kết quả: 7/7 tests passed
```

**Nếu fail:**
- Check Python version (>= 3.8)
- Check dependencies đã cài đủ chưa
- Check file paths

---

## 🧪 Test 2: Test Database & Thẻ

### Thêm thẻ test:

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
✓ [3/3] Added card ID: 3

============================================================
✅ HOÀN TẤT! Đã thêm 3/3 thẻ
============================================================
```

### Xem danh sách thẻ:

```bash
python add_test_cards.py list
```

### Test database trực tiếp:

```bash
cd ..\pay_kiro
python
```

```python
from database import CardDatabase

db = CardDatabase()

# Xem thẻ
cards = db.get_active_cards()
print(f"Có {len(cards)} thẻ")

for card in cards:
    print(f"ID {card['id']}: ****{card['card_number'][-4:]} - Priority {card['priority']}")

# Xem stats
stats = db.get_stats()
print(stats)

exit()
```

---

## 🧪 Test 3: Test Google Sheets Connection

Tạo file `test_sheets.py`:

```python
import os
from dotenv import load_dotenv
load_dotenv()

# Test import
try:
    from bot_shop import init_sheets, load_products, stock_count_ready_by_code
    print("✓ Import thành công")
except Exception as e:
    print(f"✗ Import thất bại: {e}")
    exit(1)

# Test connection
try:
    init_sheets()
    print("✓ Kết nối Google Sheets thành công")
except Exception as e:
    print(f"✗ Kết nối thất bại: {e}")
    exit(1)

# Test load products
try:
    products = load_products()
    print(f"✓ Load products thành công: {len(products)} sản phẩm")
    
    for p in products[:3]:
        print(f"   - {p['product_id']}: {p['name']}")
        if p.get('requires_payment'):
            print(f"     → Cần payment: {p['payment_url']}")
except Exception as e:
    print(f"✗ Load products thất bại: {e}")
    exit(1)

# Test stock
try:
    stock = stock_count_ready_by_code()
    print(f"✓ Load stock thành công: {len(stock)} stock codes")
    
    for code, count in list(stock.items())[:3]:
        print(f"   - {code}: {count} items")
except Exception as e:
    print(f"✗ Load stock thất bại: {e}")

print("\n✅ Tất cả tests Google Sheets đều PASS!")
```

Chạy:
```bash
cd d:\TOOl_FARM\bottele
python test_sheets.py
```

---

## 🧪 Test 4: Test Selenium (Browser Automation)

Tạo file `test_selenium.py`:

```python
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'pay_kiro'))

from payment_automation import KiroPaymentAutomation

print("Testing Selenium...")

# Test với URL đơn giản
automation = KiroPaymentAutomation(
    email="test@example.com",
    password="test123",
    payment_url="https://www.google.com",
    headless=False  # Để xem browser
)

try:
    print("1. Khởi tạo driver...")
    automation.init_driver()
    print("   ✓ Driver OK")
    
    print("2. Navigate to URL...")
    automation.driver.get("https://www.google.com")
    print("   ✓ Navigate OK")
    
    print("3. Take screenshot...")
    screenshot = automation.take_screenshot("test")
    print(f"   ✓ Screenshot saved: {screenshot}")
    
    input("\nNhấn Enter để đóng browser...")
    
    print("4. Close driver...")
    automation.close_driver()
    print("   ✓ Close OK")
    
    print("\n✅ Selenium test PASS!")
    
except Exception as e:
    print(f"\n✗ Selenium test FAIL: {e}")
    automation.close_driver()
```

Chạy:
```bash
cd d:\TOOl_FARM\bottele
python test_selenium.py
```

**Kết quả:**
- Browser Chrome sẽ mở
- Navigate đến Google
- Chụp screenshot
- Đợi bạn nhấn Enter
- Đóng browser

---

## 🧪 Test 5: Test Bot Commands (Không cần user)

Tạo file `test_bot_commands.py`:

```python
import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'pay_kiro'))

from integrated_payment import IntegratedPaymentService

async def test_commands():
    print("Testing Bot Commands...")
    
    # Test payment service
    print("\n1. Test IntegratedPaymentService...")
    service = IntegratedPaymentService()
    print("   ✓ Service initialized")
    
    # Test get stats
    print("\n2. Test get_payment_stats...")
    stats = service.get_payment_stats()
    print(f"   ✓ Stats:")
    print(f"      - Active cards: {stats['active_cards']}")
    print(f"      - Success: {stats['success_transactions']}")
    print(f"      - Failed: {stats['failed_transactions']}")
    print(f"      - Success rate: {stats['success_rate']:.1f}%")
    
    # Test get cards
    print("\n3. Test get cards...")
    cards = service.card_db.get_active_cards()
    print(f"   ✓ Found {len(cards)} cards:")
    for card in cards[:3]:
        print(f"      - ID {card['id']}: ****{card['card_number'][-4:]} (Priority {card['priority']})")
    
    print("\n✅ All command tests PASS!")

asyncio.run(test_commands())
```

Chạy:
```bash
cd d:\TOOl_FARM\bottele
python test_bot_commands.py
```

---

## 🧪 Test 6: Test Flow Mua Hàng (Không Payment)

### Chuẩn bị:
1. Thêm product KHÔNG cần payment vào Google Sheets:

| product_id | name | price | stock_code | requires_payment |
|------------|------|-------|------------|------------------|
| TEST_NO_PAY | Test No Payment | 10000 | TEST_POOL | no |

2. Thêm items vào POOL với stock_code = TEST_POOL

### Test:
1. Chạy bot:
```bash
cd d:\TOOl_FARM\bottele
python main.py
```

2. Trên Telegram:
   - `/start`
   - Bấm "🛍 Sản phẩm"
   - Chọn "Test No Payment"
   - Bấm "Mua"
   - Nhập số lượng: `1`

3. **Kết quả mong đợi:**
   - Bot tạo QR code
   - Hiển thị thông tin chuyển khoản
   - Đợi webhook từ SePay

4. **Test webhook (local):**
   - Dùng ngrok để expose local:
   ```bash
   ngrok http 10000
   ```
   - Copy URL ngrok vào SePay webhook config
   - Chuyển khoản test
   - Bot sẽ tự động giao hàng

---

## 🧪 Test 7: Test Flow Mua Hàng (Có Payment) ⭐

### Chuẩn bị:
1. Thêm product CẦN payment vào Google Sheets:

| product_id | name | price | stock_code | requires_payment | payment_url | account_email | account_password |
|------------|------|-------|------------|------------------|-------------|---------------|------------------|
| TEST_PAY | Test With Payment | 10000 | TEST_POOL | yes | https://httpbin.org/delay/2 | test@example.com | test123 |

**Note:** Dùng `https://httpbin.org/delay/2` để test (mock payment page)

2. Đảm bảo có thẻ trong database:
```bash
python add_test_cards.py list
```

### Test:
1. Chạy bot:
```bash
python main.py
```

2. Trên Telegram:
   - `/start`
   - Bấm "🛍 Sản phẩm"
   - Chọn "Test With Payment"
   - Bấm "Mua"
   - Nhập số lượng: `1`

3. **Kết quả mong đợi:**
   ```
   ⏳ ĐANG XỬ LÝ...
   
   🧾 Mã đơn: ORD20260510120000ABCD
   📦 SP: Test With Payment
   💰 Giá: 10.000 đ
   
   🔄 Đang tự động thanh toán...
   ⏱ Vui lòng đợi 30-60 giây...
   ```

4. **Xem browser (nếu PAYMENT_HEADLESS=False):**
   - Browser Chrome sẽ mở
   - Navigate đến payment URL
   - Thử điền thông tin thẻ
   - Submit

5. **Kết quả:**
   - Nếu thành công:
   ```
   ✅ THANH TOÁN THÀNH CÔNG
   
   🧾 Mã đơn: ORD20260510120000ABCD
   📦 SP: Test With Payment
   💰 Giá: 10.000 đ
   
   💳 Thẻ: ****8586
   
   🎁 Đang giao hàng...
   ```
   
   - Nếu thất bại:
   ```
   ❌ THANH TOÁN THẤT BẠI
   
   ⚠️ Lỗi: All cards failed
   ```

### Debug:
- Check log: `payment_automation.log`
- Check screenshots: `screenshots/`
- Set `PAYMENT_HEADLESS=False` để xem browser

---

## 🧪 Test 8: Test Webhook SePay (Local)

### Setup ngrok:
```bash
# Download ngrok: https://ngrok.com/download
ngrok http 10000
```

**Output:**
```
Forwarding  https://abc123.ngrok.io -> http://localhost:10000
```

### Cấu hình SePay:
1. Vào SePay dashboard
2. Thêm webhook URL: `https://abc123.ngrok.io/webhook/sepay`
3. Thêm API key vào header

### Test:
1. Chạy bot:
```bash
python main.py
```

2. Tạo order (flow không payment)

3. Chuyển khoản test với nội dung = order_id

4. **Kết quả mong đợi:**
   - Webhook nhận request
   - Bot tự động giao hàng
   - User nhận file .txt

### Debug webhook:
```bash
# Xem log ngrok
# Xem log bot
# Check sepay_webhook.py
```

---

## 📊 Checklist Test Hoàn Chỉnh

### Môi trường:
- [ ] Python >= 3.8
- [ ] Dependencies đã cài
- [ ] Chrome browser
- [ ] ChromeDriver (auto download)
- [ ] .env configured

### Database:
- [ ] cards.db tồn tại
- [ ] Có ít nhất 3 thẻ test
- [ ] Stats hiển thị OK

### Google Sheets:
- [ ] Connection OK
- [ ] Load products OK
- [ ] Load stock OK
- [ ] Có product test (cả 2 loại)

### Selenium:
- [ ] Browser mở được
- [ ] Navigate OK
- [ ] Screenshot OK
- [ ] Close OK

### Bot:
- [ ] Bot start OK
- [ ] Commands work
- [ ] `/payment_stats` OK
- [ ] `/list_cards` OK

### Flow không payment:
- [ ] Tạo order OK
- [ ] Tạo QR OK
- [ ] Webhook nhận OK
- [ ] Giao hàng OK

### Flow có payment:
- [ ] Tạo order OK
- [ ] Auto payment chạy
- [ ] Browser automation OK
- [ ] Retry logic OK
- [ ] Giao hàng OK

---

## 🚀 Sau khi Test Local OK

### 1. Cleanup test data:
```bash
# Xóa orders test
# Xóa transactions test
# Giữ lại thẻ test
```

### 2. Chuẩn bị deploy:
- [ ] Set `PAYMENT_HEADLESS=True`
- [ ] Update products thật
- [ ] Thêm thẻ thật (nếu có)
- [ ] Backup database

### 3. Deploy lên Render:
- [ ] Push code lên Git
- [ ] Deploy trên Render
- [ ] Set environment variables
- [ ] Test lại trên production

---

## 💡 Tips

1. **Test từng bước** - Đừng test tất cả cùng lúc
2. **Check logs** - Luôn xem log khi có lỗi
3. **Use mock URLs** - Test với httpbin.org trước
4. **Backup database** - Trước mỗi lần test
5. **Set headless=False** - Để debug dễ hơn

---

## 🐛 Common Issues

### "ChromeDriver not found"
```bash
pip install --upgrade webdriver-manager
```

### "Google Sheets connection failed"
- Check service_account.json
- Check GSHEET_ID
- Check permissions

### "No active cards"
```bash
python add_test_cards.py add
```

### "Payment timeout"
- Tăng PAYMENT_TIMEOUT
- Check network
- Check payment_url

---

## 📞 Support

Nếu gặp vấn đề:
1. Check logs
2. Check screenshots
3. Test từng component riêng
4. Hỏi tôi! 😊

---

**Chúc bạn test thành công! 🎉**
