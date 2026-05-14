# 🚀 BẮT ĐẦU Ở ĐÂY - 2 PHÚT HIỂU HẾT

## ❓ Source code này làm gì?

**Bot Telegram bán hàng tự động + Tự động thanh toán**

---

## 📁 28 files chia thành 5 nhóm:

| Nhóm | Files | Làm gì? |
|------|-------|---------|
| **1. Code chính** | 5 files | Chạy bot, xử lý mua hàng, auto payment |
| **2. Cấu hình** | 3 files | .env, requirements.txt, credentials |
| **3. Tests** | 5 files | Test trước khi deploy |
| **4. Helpers** | 6 files | Thêm thẻ, patch bot, tổ chức files |
| **5. Docs** | 9 files | Hướng dẫn (bạn đang đọc) |

---

## ⚡ Chạy bot (3 lệnh):

```bash
# 1. Cài đặt
pip install -r requirements.txt

# 2. Test
python run_all_tests.py

# 3. Chạy
python main.py
```

**Xong!** ✅

---

## 🎯 Chỉ cần biết 3 files:

1. **main.py** - Chạy bot
2. **bot_shop.py** - Code bot chính
3. **integrated_payment.py** - Auto payment

**Các files khác:** Test và documentation (không cần đọc nếu bot chạy OK)

---

## 📚 Muốn hiểu sâu hơn?

Đọc theo thứ tự:

1. **README.md** ← Đọc file này trước (5 phút)
2. **HUONG_DAN_DON_GIAN.md** ← Giải thích 28 files (5 phút)
3. **SO_DO_SOURCE_CODE.md** ← Sơ đồ trực quan (5 phút)
4. **START_HERE.md** ← Quick start chi tiết (10 phút)

---

## 🗂️ Thấy lộn xộn?

Chạy lệnh này để tự động sắp xếp:

```bash
python organize_files.py
```

Sẽ tổ chức thành:
```
bottele/
├── payment/    # Auto payment
├── scripts/    # Helper scripts
├── tests/      # Tests
├── docs/       # Documentation
└── main.py     # Entry point
```

**Từ 28 files → 5 thư mục gọn gàng**

---

## 🔄 Flow hoạt động:

### Mua hàng thường:
```
User mua → QR code → User CK → Giao hàng
```

### Mua hàng có auto payment (MỚI):
```
User mua → Bot tự thanh toán → Giao hàng ngay
```

---

## ✅ Checklist:

- [ ] Đọc **README.md**
- [ ] Chạy `python run_all_tests.py`
- [ ] Chạy `python main.py`
- [ ] Test trên Telegram
- [ ] Ready to deploy!

---

## 💡 Tips:

1. **Đọc README.md trước** - Hiểu tổng quan
2. **Test local trước** - Trước khi deploy
3. **Chỉ đọc 3 files chính** - Đừng đọc hết 28 files
4. **Tổ chức files nếu muốn** - Chạy `organize_files.py`

---

## 🚀 Bước tiếp theo:

### Đọc hướng dẫn:
```
README.md
```

### Hoặc chạy luôn:
```bash
python main.py
```

---

**Chúc bạn thành công! 🎉**

---

## 📞 Cần giúp?

- **Không hiểu source code?** → Đọc `HUONG_DAN_DON_GIAN.md`
- **Muốn xem sơ đồ?** → Đọc `SO_DO_SOURCE_CODE.md`
- **Muốn quick start?** → Đọc `START_HERE.md`
- **Muốn chi tiết?** → Đọc `INTEGRATION_GUIDE.md`

---

**Made with ❤️ by Kiro AI**
