# 🤖 Shop Bot - Hướng Dẫn Đơn Giản

## 🎯 Bot này làm gì?

1. **Bán hàng tự động** qua Telegram
2. **Nhận tiền qua SePay** → Tự động giao hàng
3. **Tự động thanh toán** khi mua account (tính năng mới)

---

## ⚡ Chạy Bot (3 bước)

### Bước 1: Cài đặt
```bash
pip install -r requirements.txt
```

### Bước 2: Cấu hình file .env
```env
BOT_TOKEN=your_telegram_bot_token
GSHEET_ID=your_google_sheet_id
SEPAY_TOKEN=your_sepay_token
```

### Bước 3: Chạy
```bash
python main.py
```

**Xong! Bot đã chạy** ✅

---

## 🧪 Test Trước Khi Deploy

```bash
# Chạy tất cả tests (50 giây)
python run_all_tests.py
```

Nếu thấy `4/4 tests pass` → OK! 🎉

---

## 📁 Files Quan Trọng (Chỉ cần biết 5 files)

| File | Làm gì? | Khi nào dùng? |
|------|---------|---------------|
| **main.py** | Chạy bot | `python main.py` |
| **bot_shop.py** | Code bot chính | Đừng sửa |
| **integrated_payment.py** | Auto payment | Đừng sửa |
| **.env** | Cấu hình | Sửa token ở đây |
| **requirements.txt** | Dependencies | `pip install -r requirements.txt` |

**Các files khác:** Documentation và test scripts (không cần đọc nếu bot chạy OK)

---

## 🔧 Tính Năng Auto Payment (Mới)

### Khi nào dùng?
Khi bạn bán **account** (Netflix, Spotify, v.v.) và muốn bot **tự động mua** account từ nguồn khác.

### Cách setup:

#### 1. Thêm thẻ thanh toán
```bash
python add_test_cards.py add
```

Nhập thông tin thẻ (hoặc dùng thẻ test).

#### 2. Thêm cột vào Google Sheets

Vào sheet **PRODUCTS**, thêm 2 cột:
- `requires_payment` → Điền `yes` hoặc `no`
- `payment_link` → Link mua account (nếu `yes`)

Ví dụ:
```
| name          | price | requires_payment | payment_link              |
|---------------|-------|------------------|---------------------------|
| Netflix 1M    | 50000 | yes              | https://shop.com/netflix  |
| Spotify 1M    | 30000 | no               |                           |
```

#### 3. Xong!

Khi user mua **Netflix 1M**:
- Bot tự động vào `https://shop.com/netflix`
- Dùng thẻ để thanh toán
- Lấy account
- Giao cho user

Khi user mua **Spotify 1M**:
- Bot tạo QR code
- User chuyển khoản
- Bot giao hàng

---

## 📊 Flow Hoạt Động

### Sản phẩm KHÔNG cần payment (bình thường):
```
User mua → Bot tạo QR → User CK → Webhook → Giao hàng
```

### Sản phẩm CẦN payment (tự động):
```
User mua → Bot tự thanh toán → Giao hàng ngay (30s)
```

---

## 🐛 Gặp Lỗi?

### Bot không chạy:
```bash
# Check dependencies
pip install -r requirements.txt

# Check .env
# Đảm bảo có BOT_TOKEN, GSHEET_ID
```

### Test fail:
```bash
# Cài lại dependencies
pip install -r requirements.txt

# Thêm thẻ test
python add_test_cards.py add
```

### Auto payment không hoạt động:
```bash
# Check Chrome installed
chrome --version

# Update webdriver
pip install --upgrade webdriver-manager

# Check thẻ
python add_test_cards.py list
```

---

## 📚 Muốn Đọc Thêm?

Nếu muốn hiểu sâu hơn, đọc theo thứ tự:

1. **START_HERE.md** - Quick start (5 phút)
2. **QUICK_START_PAYMENT.md** - Setup payment (10 phút)
3. **INTEGRATION_GUIDE.md** - Chi tiết (30 phút)

**Nhưng không bắt buộc!** Bot chạy OK là được rồi.

---

## 🚀 Deploy Lên Render

### 1. Test local OK:
```bash
python run_all_tests.py
```

### 2. Push code:
```bash
git add .
git commit -m "Update bot"
git push
```

### 3. Deploy trên Render:
- Tạo Web Service
- Connect GitHub repo
- Set env variables (BOT_TOKEN, GSHEET_ID, v.v.)
- Deploy!

### 4. Set headless mode:
Trên Render, thêm env variable:
```
PAYMENT_HEADLESS=True
```

---

## 💡 Tips

1. **Test local trước** - Đừng deploy ngay
2. **Backup database** - Trước mỗi test
3. **Check logs** - Khi có lỗi
4. **Đọc START_HERE.md** - Nếu cần chi tiết

---

## 🗂️ Tổ Chức Files (Optional)

Nếu thấy quá nhiều files lộn xộn, chạy:

```bash
python organize_files.py
```

Sẽ tự động sắp xếp thành:
```
bottele/
├── payment/    # Auto payment code
├── scripts/    # Helper scripts
├── tests/      # Test files
├── docs/       # Documentation
└── main.py     # Entry point
```

**Nhưng không bắt buộc!** Bot vẫn chạy OK với structure hiện tại.

---

## ✅ Checklist

- [ ] Đã cài dependencies: `pip install -r requirements.txt`
- [ ] Đã config .env
- [ ] Đã test: `python run_all_tests.py`
- [ ] Bot chạy OK: `python main.py`
- [ ] Đã test trên Telegram
- [ ] Ready to deploy!

---

## 📞 Cần Giúp?

- **Logs:** `payment_automation.log`
- **Screenshots:** `screenshots/`
- **Database:** `cards.db`

---

**Chúc bạn thành công! 🎉**
