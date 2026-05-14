# 📖 HƯỚNG DẪN ĐỌC SOURCE CODE

## 🎯 Bạn chỉ cần biết 3 files chính:

### 1. **main.py** - File chạy bot
```bash
python main.py
```
Đây là file khởi động bot. Chạy file này là bot sẽ hoạt động.

---

### 2. **bot_shop.py** - Code bot Telegram
Đây là file chứa toàn bộ logic của bot:
- Xử lý lệnh `/start`, `/admin`
- Hiển thị sản phẩm
- Xử lý mua hàng
- Tạo QR code thanh toán

**Bạn KHÔNG cần sửa file này** trừ khi muốn thay đổi cách bot hoạt động.

---

### 3. **integrated_payment.py** - Tự động thanh toán
Đây là tính năng mới - tự động thanh toán khi mua account:
- Lấy thẻ từ database
- Mở browser tự động
- Điền thông tin thẻ
- Thanh toán
- Trả về kết quả

**Bạn KHÔNG cần sửa file này** trừ khi muốn thay đổi cách thanh toán.

---

## 📁 Các files khác là gì?

### Files cấu hình:
- **.env** - Cấu hình token, API keys
- **requirements.txt** - Danh sách thư viện cần cài
- **service_account.json** - Google Sheets credentials

### Files phụ trợ:
- **sepay_webhook.py** - Webhook nhận thông báo từ SePay
- **import_pool.py** - Import items từ Google Sheets

### Files test:
- **test_*.py** - Các file test (4 files)
- **run_all_tests.py** - Chạy tất cả tests

### Files helper:
- **add_test_cards.py** - Thêm/xem thẻ thanh toán
- **bot_shop_payment_patch.py** - Tự động patch bot
- **organize_files.py** - Tổ chức lại files

### Files documentation (9 files):
- **README.md** - Hướng dẫn chính (ĐỌC FILE NÀY)
- **START_HERE.md** - Quick start
- **QUICK_START_PAYMENT.md** - Setup payment
- **INTEGRATION_GUIDE.md** - Chi tiết tích hợp
- **LOCAL_TEST_GUIDE.md** - Hướng dẫn test
- **SUMMARY.md** - Tổng kết
- **STRUCTURE.md** - Cấu trúc code
- **README_SIMPLE.md** - README đơn giản
- **README_PAYMENT_INTEGRATION.md** - Reference payment
- **README_TEST_LOCAL.md** - Test local

---

## 🔄 Flow Hoạt Động (Đơn Giản)

### Khi user mua sản phẩm THƯỜNG:
```
1. User bấm "Mua" trên Telegram
2. bot_shop.py tạo QR code
3. User chuyển khoản
4. sepay_webhook.py nhận thông báo
5. bot_shop.py giao hàng
```

### Khi user mua sản phẩm CÓ AUTO PAYMENT:
```
1. User bấm "Mua" trên Telegram
2. bot_shop.py gọi integrated_payment.py
3. integrated_payment.py tự động thanh toán
4. bot_shop.py giao hàng ngay
```

---

## 🎯 Muốn Sửa Gì?

### Thay đổi cách bot hiển thị:
→ Sửa **bot_shop.py**

### Thay đổi cách thanh toán tự động:
→ Sửa **integrated_payment.py**

### Thay đổi webhook SePay:
→ Sửa **sepay_webhook.py**

### Thay đổi cấu hình:
→ Sửa **.env**

---

## 📊 Cấu Trúc Thư Mục (Hiện Tại)

```
bottele/
├── main.py                          ← Chạy bot
├── bot_shop.py                      ← Code bot chính
├── integrated_payment.py            ← Auto payment
├── sepay_webhook.py                 ← Webhook
├── import_pool.py                   ← Import items
│
├── .env                             ← Cấu hình
├── requirements.txt                 ← Dependencies
├── service_account.json             ← Google credentials
│
├── add_test_cards.py                ← Thêm thẻ
├── bot_shop_payment_patch.py        ← Patch bot
├── organize_files.py                ← Tổ chức files
│
├── test_integration.py              ← Test 1
├── test_bot_commands.py             ← Test 2
├── test_sheets.py                   ← Test 3
├── test_selenium.py                 ← Test 4
├── run_all_tests.py                 ← Chạy tất cả tests
│
└── README.md + 8 docs khác          ← Documentation
```

**Tổng cộng: 28 files**

---

## 🗂️ Muốn Gọn Hơn?

Chạy lệnh này để tự động sắp xếp:

```bash
python organize_files.py
```

Sẽ thành:
```
bottele/
├── payment/        # 2 files (integrated_payment.py)
├── scripts/        # 3 files (add_cards, patch, test_all)
├── tests/          # 4 files (test_*.py)
├── docs/           # 9 files (README, guides)
└── main.py + 4 files chính
```

**Từ 28 files → 5 thư mục + 5 files**

---

## ✅ Tóm Tắt

### Chỉ cần nhớ:
1. **main.py** - Chạy bot
2. **bot_shop.py** - Code bot
3. **integrated_payment.py** - Auto payment
4. **.env** - Cấu hình

### Các files khác:
- Test files (5 files) - Để test
- Helper scripts (3 files) - Tiện ích
- Documentation (9 files) - Hướng dẫn

### Không hiểu?
→ Đọc **README.md** (file vừa tạo)

### Muốn test?
→ Chạy `python run_all_tests.py`

### Muốn chạy bot?
→ Chạy `python main.py`

---

## 💡 Lời Khuyên

1. **Đừng đọc hết 28 files** - Chỉ cần đọc 3 files chính
2. **Đọc README.md trước** - Hiểu tổng quan
3. **Test trước khi deploy** - Chạy `run_all_tests.py`
4. **Tổ chức files nếu muốn** - Chạy `organize_files.py`

---

**Chúc bạn code vui! 🚀**
