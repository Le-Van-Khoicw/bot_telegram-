# 🔗 Hướng dẫn tích hợp Auto Payment vào Shop Bot

## 📋 Tổng quan

Tích hợp `pay_kiro` vào `bottele` để tự động thanh toán khi user mua account cần payment link.

### Flow hoạt động:

```
User bấm mua → Bot tạo order → Check cần payment? 
                                      ↓ YES
                                Auto thanh toán
                                      ↓
                            Success → Giao hàng
                            Failed → Thông báo lỗi
```

---

## 🛠️ Bước 1: Cập nhật Google Sheets

### Sheet PRODUCTS - Thêm các cột mới:

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `requires_payment` | Text | Có cần auto payment không | `yes` / `no` |
| `payment_url` | Text | Link thanh toán | `https://kiro.ai/payment` |
| `payment_provider` | Text | Nhà cung cấp | `kiro`, `stripe`, `custom` |
| `account_email` | Text | Email account cần thanh toán | `user@example.com` |
| `account_password` | Text | Password account | `password123` |

### Ví dụ data:

| product_id | name | price | stock_code | requires_payment | payment_url | account_email |
|------------|------|-------|------------|------------------|-------------|---------------|
| KIRO_PRO | Kiro Pro 1M | 350000 | KIRO_ACC | yes | https://kiro.ai/payment | user@example.com |
| CHATGPT_PLUS | ChatGPT Plus | 200000 | GPT_ACC | no | | |

---

## 🛠️ Bước 2: Copy thư mục pay_kiro

```bash
# Đảm bảo cấu trúc thư mục:
TOOl_FARM/
├── bottele/
│   ├── bot_shop.py
│   ├── integrated_payment.py  # ✅ Đã tạo
│   └── ...
└── pay_kiro/
    ├── database.py
    ├── payment_automation.py
    └── cards.db
```

---

## 🛠️ Bước 3: Cập nhật bot_shop.py

### 3.1 Import integrated_payment

Thêm vào đầu file `bot_shop.py`:

```python
# Thêm import
from integrated_payment import (
    IntegratedPaymentService,
    ProductWithPayment,
    handle_order_with_auto_payment
)
```

### 3.2 Cập nhật hàm load_products

Sửa hàm `load_products()` để support payment fields:

```python
def load_products() -> List[Dict[str, Any]]:
    init_sheets()
    rows = get_all_records(_ws_products)
    out: List[Dict[str, Any]] = []
    for r in rows:
        product_id = (r.get("product_id") or "").strip()
        name = (r.get("name") or "").strip()
        stock_code = (r.get("stock_code") or "").strip()
        price = normalize_int(r.get("price"), 0)
        desc = (r.get("description") or "").strip()
        
        # ✅ Thêm payment fields
        requires_payment = (r.get("requires_payment") or "no").strip().lower() == "yes"
        payment_url = (r.get("payment_url") or "").strip()
        payment_provider = (r.get("payment_provider") or "custom").strip()
        account_email = (r.get("account_email") or "").strip()
        account_password = (r.get("account_password") or "").strip()

        if product_id and stock_code and name:
            out.append({
                "product_id": product_id,
                "name": name,
                "price": price,
                "stock_code": stock_code,
                "description": desc,
                # ✅ Payment fields
                "requires_payment": requires_payment,
                "payment_url": payment_url,
                "payment_provider": payment_provider,
                "account_email": account_email,
                "account_password": account_password,
            })
    return out
```

### 3.3 Cập nhật callback xử lý mua hàng

Tìm hàm xử lý khi user bấm mua (callback `buy_*`), thêm logic auto payment:

```python
async def handle_buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý khi user bấm mua"""
    query = update.callback_query
    await query.answer()
    
    # Parse callback data
    data = query.data  # format: "buy_PRODUCT_ID_QTY"
    parts = data.split("_")
    product_id = parts[1]
    qty = int(parts[2]) if len(parts) > 2 else 1
    
    # Lấy product info
    product = find_product_by_id(product_id)
    if not product:
        await query.edit_message_text("❌ Sản phẩm không tồn tại")
        return
    
    # ✅ CHECK: Product có cần auto payment không?
    if product.get('requires_payment', False):
        await handle_buy_with_auto_payment(query, context, product, qty)
    else:
        # Flow cũ: không cần payment
        await handle_buy_normal(query, context, product, qty)


async def handle_buy_with_auto_payment(query, context, product: Dict, qty: int):
    """Xử lý mua với auto payment"""
    user_id = query.from_user.id
    
    # 1. Tạo order_id
    order_id = generate_order_id()
    
    # 2. Gửi thông báo đang xử lý
    await query.edit_message_text(
        f"⏳ *ĐANG XỬ LÝ...*\n\n"
        f"🧾 Mã đơn: `{order_id}`\n"
        f"📦 SP: {product['name']}\n"
        f"💰 Giá: {fmt_price(product['price'] * qty)}\n\n"
        f"🔄 Đang tự động thanh toán...\n"
        f"⏱ Vui lòng đợi 30-60 giây...",
        parse_mode="Markdown"
    )
    
    # 3. Gọi auto payment
    try:
        result = await handle_order_with_auto_payment(
            order_id=order_id,
            product=ProductWithPayment(product),
            user_id=user_id,
            qty=qty
        )
        
        # 4. Xử lý kết quả
        if result['success']:
            # Payment thành công
            payment_result = result['payment_result']
            
            await query.edit_message_text(
                f"✅ *THANH TOÁN THÀNH CÔNG*\n\n"
                f"🧾 Mã đơn: `{order_id}`\n"
                f"📦 SP: {product['name']}\n"
                f"💰 Giá: {fmt_price(product['price'] * qty)}\n\n"
                f"💳 Thẻ: {payment_result['card_used']}\n\n"
                f"🎁 Đang giao hàng...",
                parse_mode="Markdown"
            )
            
            # ✅ Giao hàng (dùng logic cũ)
            items = await gs_call(
                mark_sold_and_get_secrets,
                order_id
            )
            
            if items:
                secrets = [it['secret'] for it in items]
                await send_delivery_message(
                    user_id,
                    order_id,
                    product['stock_code'],
                    qty,
                    secrets
                )
                
                await query.message.reply_text(
                    "✅ *ĐÃ GIAO HÀNG THÀNH CÔNG*\n\n"
                    "📄 Thông tin đã được gửi ở tin nhắn phía trên.",
                    parse_mode="Markdown"
                )
        else:
            # Payment thất bại
            error = result.get('error', 'Unknown error')
            
            await query.edit_message_text(
                f"❌ *THANH TOÁN THẤT BẠI*\n\n"
                f"🧾 Mã đơn: `{order_id}`\n"
                f"📦 SP: {product['name']}\n\n"
                f"⚠️ Lỗi: {error}\n\n"
                f"💬 Vui lòng liên hệ admin để được hỗ trợ.",
                parse_mode="Markdown",
                reply_markup=kb_support_only()
            )
            
    except Exception as e:
        logger.exception(f"Auto payment error: {e}")
        
        await query.edit_message_text(
            f"❌ *LỖI HỆ THỐNG*\n\n"
            f"🧾 Mã đơn: `{order_id}`\n\n"
            f"⚠️ Đã xảy ra lỗi khi xử lý thanh toán.\n"
            f"💬 Vui lòng liên hệ admin.",
            parse_mode="Markdown",
            reply_markup=kb_support_only()
        )


async def handle_buy_normal(query, context, product: Dict, qty: int):
    """Xử lý mua bình thường (không cần payment)"""
    # Logic cũ của bạn
    # ... (giữ nguyên code cũ)
    pass
```

---

## 🛠️ Bước 4: Thêm Admin Commands

Thêm vào cuối file `bot_shop.py`:

```python
# ============= ADMIN: PAYMENT MANAGEMENT =============

async def cmd_payment_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command /payment_stats - Xem thống kê payment"""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Không có quyền")
        return
    
    from integrated_payment import IntegratedPaymentService
    
    service = IntegratedPaymentService()
    stats = service.get_payment_stats()
    
    text = (
        "📊 *THỐNG KÊ THANH TOÁN*\n\n"
        f"💳 Thẻ active: {stats['active_cards']}\n"
        f"✅ Thành công: {stats['success_transactions']}\n"
        f"❌ Thất bại: {stats['failed_transactions']}\n"
        f"📈 Tỷ lệ: {stats['success_rate']:.1f}%"
    )
    
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_list_cards(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command /list_cards - Xem danh sách thẻ"""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Không có quyền")
        return
    
    from integrated_payment import IntegratedPaymentService
    
    service = IntegratedPaymentService()
    cards = service.card_db.get_active_cards()
    
    if not cards:
        await update.message.reply_text("Không có thẻ nào")
        return
    
    text = f"💳 *DANH SÁCH THẺ* ({len(cards)} thẻ)\n\n"
    
    for card in cards[:10]:  # Chỉ show 10 thẻ đầu
        text += (
            f"🆔 ID: {card['id']}\n"
            f"💳 Số: ****{card['card_number'][-4:]}\n"
            f"👤 Tên: {card['card_holder']}\n"
            f"✅ Thành công: {card['success_count']} | "
            f"❌ Thất bại: {card['fail_count']}\n"
            f"⭐ Priority: {card['priority']}\n"
            f"{'─' * 30}\n"
        )
    
    await update.message.reply_text(text, parse_mode="Markdown")


# Đăng ký handlers
def main():
    # ... existing code ...
    
    # ✅ Thêm payment commands
    application.add_handler(CommandHandler("payment_stats", cmd_payment_stats))
    application.add_handler(CommandHandler("list_cards", cmd_list_cards))
    
    # ... rest of code ...
```

---

## 🛠️ Bước 5: Cấu hình Environment

Thêm vào file `.env`:

```env
# ============= AUTO PAYMENT CONFIG =============

# Chạy headless hay không (True = không hiện browser)
PAYMENT_HEADLESS=True

# Số thẻ tối đa thử khi thanh toán
MAX_RETRY_CARDS=3

# Timeout cho mỗi lần thanh toán (giây)
PAYMENT_TIMEOUT=60
```

---

## 🛠️ Bước 6: Setup Database thẻ

Chạy script để thêm thẻ test:

```python
# add_test_cards.py
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'pay_kiro'))

from database import CardDatabase

db = CardDatabase()

# Thêm thẻ test
test_cards = [
    {
        'card_number': '4154620022238586',
        'card_holder': 'NGUYEN VAN A',
        'expiry_month': '12',
        'expiry_year': '29',
        'cvv': '123',
        'billing_address': '123 Test Street',
        'billing_city': 'Hanoi',
        'billing_state': 'Hanoi',
        'billing_zip': '100000',
        'billing_country': 'Vietnam',
        'priority': 1,
        'notes': 'Thẻ test 1'
    },
    {
        'card_number': '5200000000001096',
        'card_holder': 'TRAN THI B',
        'expiry_month': '06',
        'expiry_year': '28',
        'cvv': '456',
        'billing_address': '456 Test Avenue',
        'billing_city': 'HCMC',
        'billing_state': 'HCMC',
        'billing_zip': '700000',
        'billing_country': 'Vietnam',
        'priority': 2,
        'notes': 'Thẻ test 2'
    }
]

for card in test_cards:
    card_id = db.add_card(card)
    print(f"✓ Added card ID: {card_id} - ****{card['card_number'][-4:]}")

print("\n✅ Done! Added", len(test_cards), "cards")
```

Chạy:
```bash
cd d:\TOOl_FARM\bottele
python add_test_cards.py
```

---

## 🧪 Bước 7: Test

### Test 1: Thêm product có payment vào Google Sheets

| product_id | name | price | stock_code | requires_payment | payment_url | account_email | account_password |
|------------|------|-------|------------|------------------|-------------|---------------|------------------|
| TEST_PAYMENT | Test Payment Product | 10000 | TEST_POOL | yes | https://example.com/payment | test@example.com | password123 |

### Test 2: Chạy bot và test mua

```bash
cd d:\TOOl_FARM\bottele
python main.py
```

Trên Telegram:
1. `/start`
2. Bấm "🛍 Sản phẩm"
3. Chọn "Test Payment Product"
4. Bấm "Mua"
5. Bot sẽ tự động thanh toán và giao hàng

### Test 3: Kiểm tra stats

```
/payment_stats
```

Sẽ hiển thị:
```
📊 THỐNG KÊ THANH TOÁN

💳 Thẻ active: 2
✅ Thành công: 1
❌ Thất bại: 0
📈 Tỷ lệ: 100.0%
```

---

## 🎯 Kết quả

### Trước khi tích hợp:
```
User mua → Bot reserve items → User chuyển khoản → Admin check → Giao hàng
```

### Sau khi tích hợp:
```
User mua → Bot auto thanh toán → Giao hàng ngay
```

**Lợi ích:**
- ✅ Tự động 100%
- ✅ Giao hàng tức thì
- ✅ Không cần admin can thiệp
- ✅ Tự động retry khi thẻ lỗi
- ✅ Tracking đầy đủ

---

## 🐛 Troubleshooting

### Lỗi: "No active cards available"
**Giải pháp:** Chạy `add_test_cards.py` để thêm thẻ

### Lỗi: "Failed to navigate to payment page"
**Giải pháp:** 
- Kiểm tra `payment_url` có đúng không
- Kiểm tra ChromeDriver đã cài chưa
- Set `PAYMENT_HEADLESS=False` để xem browser

### Lỗi: "All cards failed"
**Giải pháp:**
- Kiểm tra thẻ có valid không
- Kiểm tra selector trong `payment_automation.py`
- Xem log trong `payment_automation.log`

### Payment chậm
**Giải pháp:**
- Giảm `PAYMENT_TIMEOUT`
- Tăng `MAX_RETRY_CARDS`
- Optimize selector trong code

---

## 📞 Support

Nếu gặp vấn đề, check:
1. Log file: `payment_automation.log`
2. Screenshots: `screenshots/`
3. Database: `cards.db`

Hoặc hỏi tôi! 😊
