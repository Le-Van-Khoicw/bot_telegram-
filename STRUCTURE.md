# 📁 Cấu trúc Source Code - Tổ chức lại

## 🎯 Mục tiêu

Tổ chức lại source code thành cấu trúc rõ ràng, dễ hiểu:

```
bottele/
├── core/                    # Code chính
│   ├── bot_shop.py         # Bot chính (giữ nguyên)
│   ├── sepay_webhook.py    # Webhook (giữ nguyên)
│   └── import_pool.py      # Import pool (giữ nguyên)
│
├── payment/                 # ✨ MỚI - Auto payment
│   ├── __init__.py
│   ├── service.py          # Payment service
│   └── models.py           # Payment models
│
├── scripts/                 # ✨ MỚI - Helper scripts
│   ├── add_cards.py        # Thêm thẻ
│   ├── patch_bot.py        # Patch bot
│   └── test_all.py         # Test tất cả
│
├── tests/                   # ✨ MỚI - Test files
│   ├── test_integration.py
│   ├── test_commands.py
│   ├── test_sheets.py
│   └── test_selenium.py
│
├── docs/                    # ✨ MỚI - Documentation
│   ├── 01_START_HERE.md
│   ├── 02_QUICK_START.md
│   ├── 03_INTEGRATION.md
│   └── 04_TEST_GUIDE.md
│
├── main.py                  # Entry point (giữ nguyên)
├── .env                     # Config (giữ nguyên)
└── requirements.txt         # Dependencies (giữ nguyên)
```

---

## 🔄 Di chuyển files

### Bước 1: Tạo thư mục

```bash
cd d:\TOOl_FARM\bottele

mkdir payment
mkdir scripts
mkdir tests
mkdir docs
```

### Bước 2: Di chuyển files

**Payment files → payment/**
- `integrated_payment.py` → `payment/service.py`

**Helper scripts → scripts/**
- `add_test_cards.py` → `scripts/add_cards.py`
- `bot_shop_payment_patch.py` → `scripts/patch_bot.py`
- `run_all_tests.py` → `scripts/test_all.py`

**Test files → tests/**
- `test_integration.py` → `tests/test_integration.py`
- `test_bot_commands.py` → `tests/test_commands.py`
- `test_sheets.py` → `tests/test_sheets.py`
- `test_selenium.py` → `tests/test_selenium.py`

**Documentation → docs/**
- `START_HERE.md` → `docs/01_START_HERE.md`
- `QUICK_START_PAYMENT.md` → `docs/02_QUICK_START.md`
- `INTEGRATION_GUIDE.md` → `docs/03_INTEGRATION.md`
- `LOCAL_TEST_GUIDE.md` → `docs/04_TEST_GUIDE.md`
- `SUMMARY.md` → `docs/05_SUMMARY.md`
- `README_PAYMENT_INTEGRATION.md` → `docs/06_REFERENCE.md`
- `README_TEST_LOCAL.md` → `docs/07_TEST_LOCAL.md`

---

## 📝 Cấu trúc mới (Gọn gàng)

```
bottele/
│
├── 📂 core/                 # Code chính của bot
│   ├── bot_shop.py         # Bot Telegram chính
│   ├── sepay_webhook.py    # Webhook SePay
│   └── import_pool.py      # Import pool items
│
├── 📂 payment/              # Module auto payment
│   ├── __init__.py         # Package init
│   ├── service.py          # IntegratedPaymentService
│   └── models.py           # ProductWithPayment
│
├── 📂 scripts/              # Scripts tiện ích
│   ├── add_cards.py        # Thêm/xem thẻ
│   ├── patch_bot.py        # Patch bot tự động
│   └── test_all.py         # Chạy tất cả tests
│
├── 📂 tests/                # Test suite
│   ├── test_integration.py # Test tích hợp
│   ├── test_commands.py    # Test commands
│   ├── test_sheets.py      # Test Google Sheets
│   └── test_selenium.py    # Test Selenium
│
├── 📂 docs/                 # Documentation
│   ├── 01_START_HERE.md    # Bắt đầu
│   ├── 02_QUICK_START.md   # Quick start
│   ├── 03_INTEGRATION.md   # Integration guide
│   ├── 04_TEST_GUIDE.md    # Test guide
│   ├── 05_SUMMARY.md       # Tổng kết
│   ├── 06_REFERENCE.md     # Reference
│   └── 07_TEST_LOCAL.md    # Test local
│
├── 📄 main.py              # Entry point
├── 📄 .env                 # Environment config
├── 📄 requirements.txt     # Dependencies
├── 📄 README.md            # Main README
└── 📄 service_account.json # Google credentials
```

---

## 🎯 Lợi ích

### Trước (Lộn xộn):
```
bottele/
├── bot_shop.py
├── integrated_payment.py
├── add_test_cards.py
├── test_integration.py
├── test_bot_commands.py
├── test_sheets.py
├── test_selenium.py
├── bot_shop_payment_patch.py
├── run_all_tests.py
├── START_HERE.md
├── QUICK_START_PAYMENT.md
├── INTEGRATION_GUIDE.md
├── LOCAL_TEST_GUIDE.md
├── SUMMARY.md
├── README_PAYMENT_INTEGRATION.md
├── README_TEST_LOCAL.md
└── ... (17+ files ở root)
```

### Sau (Gọn gàng):
```
bottele/
├── core/           # 3 files
├── payment/        # 3 files
├── scripts/        # 3 files
├── tests/          # 4 files
├── docs/           # 7 files
└── main.py + .env  # 2 files
```

**Từ 17+ files ở root → 5 thư mục + 2 files**

---

## 🚀 Cách sử dụng sau khi tổ chức

### Chạy bot:
```bash
python main.py
```

### Thêm thẻ:
```bash
python scripts/add_cards.py add
```

### Patch bot:
```bash
python scripts/patch_bot.py
```

### Chạy tests:
```bash
python scripts/test_all.py
```

### Đọc docs:
```bash
# Bắt đầu
docs/01_START_HERE.md

# Quick start
docs/02_QUICK_START.md

# Chi tiết
docs/03_INTEGRATION.md
```

---

## 📖 Import paths mới

### Trước:
```python
from integrated_payment import IntegratedPaymentService
```

### Sau:
```python
from payment.service import IntegratedPaymentService
```

### Trước:
```python
from add_test_cards import add_test_cards
```

### Sau:
```python
from scripts.add_cards import add_test_cards
```

---

## ✅ Checklist di chuyển

- [ ] Tạo thư mục: payment, scripts, tests, docs
- [ ] Di chuyển files vào thư mục tương ứng
- [ ] Tạo `__init__.py` cho payment/
- [ ] Update import paths trong code
- [ ] Test lại: `python scripts/test_all.py`
- [ ] Update README.md

---

Bạn muốn tôi:
1. **Tạo script tự động di chuyển** files?
2. **Giữ nguyên** structure hiện tại nhưng **đơn giản hóa** code?
3. **Tạo version mới** gọn gàng hơn?

Chọn option nào bạn thích nhất? 😊
