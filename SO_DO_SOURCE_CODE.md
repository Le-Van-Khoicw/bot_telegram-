# 🗺️ SƠ ĐỒ SOURCE CODE - NHÌN LÀ HIỂU

## 📦 28 Files Chia Thành 5 Nhóm

```
┌─────────────────────────────────────────────────────────────┐
│                    BOTTELE PROJECT                          │
│                     (28 files)                              │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  NHÓM 1      │    │  NHÓM 2      │    │  NHÓM 3      │
│  CODE CHÍNH  │    │  CẤU HÌNH    │    │  TESTS       │
│  (5 files)   │    │  (3 files)   │    │  (5 files)   │
└──────────────┘    └──────────────┘    └──────────────┘
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  NHÓM 4      │    │  NHÓM 5      │    │              │
│  HELPERS     │    │  DOCS        │    │              │
│  (6 files)   │    │  (9 files)   │    │              │
└──────────────┘    └──────────────┘    └──────────────┘
```

---

## 🎯 NHÓM 1: CODE CHÍNH (5 files) ⭐ QUAN TRỌNG

```
┌─────────────────────────────────────────────────────────┐
│                     CODE CHÍNH                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. main.py                    ← Chạy bot              │
│     └─> Khởi động bot                                  │
│                                                         │
│  2. bot_shop.py                ← Bot Telegram          │
│     ├─> Xử lý lệnh /start, /admin                      │
│     ├─> Hiển thị sản phẩm                              │
│     ├─> Xử lý mua hàng                                 │
│     └─> Tạo QR code                                    │
│                                                         │
│  3. integrated_payment.py      ← Auto payment (MỚI)    │
│     ├─> Lấy thẻ từ database                            │
│     ├─> Mở browser tự động                             │
│     ├─> Điền thông tin thẻ                             │
│     └─> Thanh toán                                     │
│                                                         │
│  4. sepay_webhook.py           ← Webhook SePay         │
│     └─> Nhận thông báo thanh toán                      │
│                                                         │
│  5. import_pool.py             ← Import items          │
│     └─> Load items từ Google Sheets                    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Bạn chỉ cần hiểu 3 files: main.py, bot_shop.py, integrated_payment.py**

---

## ⚙️ NHÓM 2: CẤU HÌNH (3 files)

```
┌─────────────────────────────────────────────────────────┐
│                     CẤU HÌNH                            │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. .env                       ← Tokens & API keys     │
│     ├─> BOT_TOKEN                                      │
│     ├─> GSHEET_ID                                      │
│     ├─> SEPAY_TOKEN                                    │
│     └─> PAYMENT_HEADLESS                               │
│                                                         │
│  2. requirements.txt           ← Dependencies          │
│     └─> pip install -r requirements.txt                │
│                                                         │
│  3. service_account.json       ← Google credentials    │
│     └─> Để kết nối Google Sheets                       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Chỉ cần sửa .env khi cần thay đổi cấu hình**

---

## 🧪 NHÓM 3: TESTS (5 files)

```
┌─────────────────────────────────────────────────────────┐
│                       TESTS                             │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. run_all_tests.py           ← Chạy tất cả tests     │
│     └─> python run_all_tests.py                        │
│                                                         │
│  2. test_integration.py        ← Test tích hợp         │
│     └─> Test imports, database, service                │
│                                                         │
│  3. test_bot_commands.py       ← Test commands         │
│     └─> Test payment service, stats, cards             │
│                                                         │
│  4. test_sheets.py             ← Test Google Sheets    │
│     └─> Test connection, load products                 │
│                                                         │
│  5. test_selenium.py           ← Test browser          │
│     └─> Test automation, screenshots                   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Chạy `python run_all_tests.py` trước khi deploy**

---

## 🛠️ NHÓM 4: HELPERS (6 files)

```
┌─────────────────────────────────────────────────────────┐
│                      HELPERS                            │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. add_test_cards.py          ← Quản lý thẻ           │
│     ├─> python add_test_cards.py add                   │
│     └─> python add_test_cards.py list                  │
│                                                         │
│  2. bot_shop_payment_patch.py  ← Patch bot tự động     │
│     └─> python bot_shop_payment_patch.py               │
│                                                         │
│  3. organize_files.py          ← Tổ chức files         │
│     └─> python organize_files.py                       │
│                                                         │
│  4. backup_manager.py          ← Backup Google Sheets  │
│     └─> Backup & restore sheets                        │
│                                                         │
│  5. performance_optimization.md ← Tối ưu hiệu suất     │
│     └─> Hướng dẫn tối ưu                               │
│                                                         │
│  6. qr.jpg                     ← QR code mẫu           │
│     └─> Ảnh QR code                                    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Dùng khi cần: thêm thẻ, patch bot, tổ chức files**

---

## 📚 NHÓM 5: DOCUMENTATION (9 files)

```
┌─────────────────────────────────────────────────────────┐
│                   DOCUMENTATION                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. README.md                  ← ĐỌC FILE NÀY TRƯỚC    │
│     └─> Hướng dẫn chính                                │
│                                                         │
│  2. HUONG_DAN_DON_GIAN.md      ← Hướng dẫn đơn giản    │
│     └─> Giải thích 28 files                            │
│                                                         │
│  3. SO_DO_SOURCE_CODE.md       ← File này              │
│     └─> Sơ đồ trực quan                                │
│                                                         │
│  4. START_HERE.md              ← Quick start           │
│     └─> Bắt đầu trong 5 phút                           │
│                                                         │
│  5. QUICK_START_PAYMENT.md     ← Setup payment         │
│     └─> Cài đặt auto payment                           │
│                                                         │
│  6. INTEGRATION_GUIDE.md       ← Chi tiết tích hợp     │
│     └─> Hướng dẫn đầy đủ                               │
│                                                         │
│  7. LOCAL_TEST_GUIDE.md        ← Test local            │
│     └─> Hướng dẫn test chi tiết                        │
│                                                         │
│  8. SUMMARY.md                 ← Tổng kết              │
│     └─> Tóm tắt dự án                                  │
│                                                         │
│  9. STRUCTURE.md               ← Cấu trúc code         │
│     └─> Đề xuất tổ chức lại                            │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Đọc theo thứ tự: README.md → HUONG_DAN_DON_GIAN.md → START_HERE.md**

---

## 🔄 FLOW HOẠT ĐỘNG

### Flow 1: Mua hàng thường (KHÔNG auto payment)

```
┌─────────┐      ┌──────────────┐      ┌──────────┐      ┌──────────────┐
│  User   │─────>│  bot_shop.py │─────>│ QR Code  │─────>│ User CK      │
│  Mua    │      │  Tạo QR      │      │          │      │              │
└─────────┘      └──────────────┘      └──────────┘      └──────────────┘
                                                                  │
                                                                  ▼
┌─────────┐      ┌──────────────┐      ┌──────────────────────────────┐
│ Giao    │<─────│  bot_shop.py │<─────│  sepay_webhook.py            │
│ hàng    │      │  Giao hàng   │      │  Nhận thông báo thanh toán   │
└─────────┘      └──────────────┘      └──────────────────────────────┘
```

### Flow 2: Mua hàng có auto payment (MỚI)

```
┌─────────┐      ┌──────────────┐      ┌─────────────────────────┐
│  User   │─────>│  bot_shop.py │─────>│ integrated_payment.py   │
│  Mua    │      │  Gọi payment │      │ Tự động thanh toán      │
└─────────┘      └──────────────┘      └─────────────────────────┘
                                                    │
                                                    ▼
                                        ┌─────────────────────┐
                                        │  1. Lấy thẻ từ DB   │
                                        │  2. Mở browser      │
                                        │  3. Điền thông tin  │
                                        │  4. Thanh toán      │
                                        └─────────────────────┘
                                                    │
                                                    ▼
┌─────────┐      ┌──────────────┐      ┌─────────────────────────┐
│ Giao    │<─────│  bot_shop.py │<─────│ integrated_payment.py   │
│ hàng    │      │  Giao hàng   │      │ Trả về kết quả          │
└─────────┘      └──────────────┘      └─────────────────────────┘
```

---

## 🎯 CÁCH ĐỌC SOURCE CODE

### Bước 1: Hiểu tổng quan (5 phút)
```
Đọc: README.md
     └─> Hiểu bot làm gì, cách chạy
```

### Bước 2: Hiểu cấu trúc (5 phút)
```
Đọc: HUONG_DAN_DON_GIAN.md
     └─> Hiểu 28 files chia thành 5 nhóm
```

### Bước 3: Hiểu flow (5 phút)
```
Đọc: SO_DO_SOURCE_CODE.md (file này)
     └─> Hiểu flow hoạt động
```

### Bước 4: Đọc code chính (30 phút)
```
Đọc theo thứ tự:
1. main.py              (50 dòng)
2. bot_shop.py          (500 dòng)
3. integrated_payment.py (400 dòng)
```

### Bước 5: Test (5 phút)
```
Chạy: python run_all_tests.py
      └─> Đảm bảo mọi thứ hoạt động
```

**Tổng thời gian: 50 phút để hiểu toàn bộ project**

---

## 📊 THỐNG KÊ

```
┌────────────────────────────────────────────────────────┐
│                  THỐNG KÊ PROJECT                      │
├────────────────────────────────────────────────────────┤
│                                                        │
│  Tổng files:           28 files                       │
│  Code chính:           5 files  (18%)                 │
│  Cấu hình:             3 files  (11%)                 │
│  Tests:                5 files  (18%)                 │
│  Helpers:              6 files  (21%)                 │
│  Documentation:        9 files  (32%)                 │
│                                                        │
│  Tổng dòng code:       ~2000 dòng                     │
│  Code chính:           ~1000 dòng (50%)               │
│  Tests:                ~500 dòng  (25%)               │
│  Helpers:              ~500 dòng  (25%)               │
│                                                        │
└────────────────────────────────────────────────────────┘
```

---

## ✅ CHECKLIST HIỂU SOURCE CODE

- [ ] Đã đọc README.md
- [ ] Đã đọc HUONG_DAN_DON_GIAN.md
- [ ] Đã đọc SO_DO_SOURCE_CODE.md (file này)
- [ ] Đã hiểu 5 nhóm files
- [ ] Đã hiểu flow hoạt động
- [ ] Đã đọc main.py
- [ ] Đã đọc bot_shop.py
- [ ] Đã đọc integrated_payment.py
- [ ] Đã chạy tests: `python run_all_tests.py`
- [ ] Đã test bot: `python main.py`

**Nếu tích hết 10 ô → Bạn đã hiểu source code! 🎉**

---

## 💡 LỜI KHUYÊN

### Đừng:
- ❌ Đọc hết 28 files
- ❌ Đọc từ đầu đến cuối
- ❌ Đọc code trước khi hiểu flow

### Nên:
- ✅ Đọc README.md trước
- ✅ Hiểu flow trước, code sau
- ✅ Chỉ đọc 3 files chính
- ✅ Test trước khi sửa code

---

## 🚀 BƯỚC TIẾP THEO

### Nếu muốn chạy bot:
```bash
python main.py
```

### Nếu muốn test:
```bash
python run_all_tests.py
```

### Nếu muốn tổ chức files:
```bash
python organize_files.py
```

### Nếu muốn thêm thẻ:
```bash
python add_test_cards.py add
```

---

**Chúc bạn đọc code vui vẻ! 📖✨**
