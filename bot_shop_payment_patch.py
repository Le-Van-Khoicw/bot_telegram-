"""
Patch để thêm auto payment vào bot_shop.py
Chạy file này để tự động thêm code cần thiết
"""

import os
import re


def backup_file(filepath):
    """Backup file trước khi patch"""
    backup_path = filepath + '.backup'
    
    if os.path.exists(backup_path):
        print(f"⚠️  Backup đã tồn tại: {backup_path}")
        response = input("Ghi đè backup? (y/n): ")
        if response.lower() != 'y':
            return False
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✓ Đã backup: {backup_path}")
    return True


def add_import_section(content):
    """Thêm import section"""
    
    # Tìm vị trí sau các import hiện tại
    import_pattern = r'(from bot_shop import.*?\n)'
    
    new_imports = """
# ============= AUTO PAYMENT INTEGRATION =============
from integrated_payment import (
    IntegratedPaymentService,
    ProductWithPayment,
    handle_order_with_auto_payment
)
# ====================================================

"""
    
    # Check xem đã có import chưa
    if 'integrated_payment' in content:
        print("⚠️  Import đã tồn tại, bỏ qua")
        return content
    
    # Thêm sau dòng import cuối
    lines = content.split('\n')
    insert_pos = 0
    
    for i, line in enumerate(lines):
        if line.startswith('import ') or line.startswith('from '):
            insert_pos = i + 1
    
    lines.insert(insert_pos, new_imports)
    
    print("✓ Đã thêm import section")
    return '\n'.join(lines)


def update_load_products(content):
    """Update hàm load_products"""
    
    # Tìm hàm load_products
    pattern = r'(def load_products\(\).*?return out)'
    
    match = re.search(pattern, content, re.DOTALL)
    
    if not match:
        print("⚠️  Không tìm thấy hàm load_products")
        return content
    
    old_func = match.group(0)
    
    # Check xem đã update chưa
    if 'requires_payment' in old_func:
        print("⚠️  load_products đã được update, bỏ qua")
        return content
    
    # Thêm payment fields vào dict
    new_append = """
        # ✅ Payment fields
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
    return out"""
    
    # Replace phần append
    new_func = re.sub(
        r'if product_id and stock_code and name:.*?return out',
        new_append,
        old_func,
        flags=re.DOTALL
    )
    
    content = content.replace(old_func, new_func)
    
    print("✓ Đã update load_products()")
    return content


def add_payment_handlers(content):
    """Thêm payment handlers"""
    
    # Check xem đã có chưa
    if 'handle_buy_with_auto_payment' in content:
        print("⚠️  Payment handlers đã tồn tại, bỏ qua")
        return content
    
    handlers_code = '''

# ============= AUTO PAYMENT HANDLERS =============

async def handle_buy_with_auto_payment(query, context, product: Dict, qty: int):
    """Xử lý mua với auto payment"""
    user_id = query.from_user.id
    
    # 1. Tạo order_id
    order_id = generate_order_id()
    
    # 2. Reserve items từ pool
    items = await gs_call(
        reserve_items_from_pool,
        product['stock_code'],
        qty,
        order_id,
        ORDER_TTL_SECONDS
    )
    
    if not items:
        await query.edit_message_text(
            "❌ *HẾT HÀNG*\\n\\n"
            f"Sản phẩm `{product['name']}` hiện đã hết hàng.\\n"
            "Vui lòng thử lại sau.",
            parse_mode="Markdown"
        )
        return
    
    # 3. Tạo order trong ORDERS
    await gs_call(append_order, {
        "order_id": order_id,
        "user_id": user_id,
        "stock_code": product['stock_code'],
        "qty": qty,
        "total": product['price'] * qty,
        "status": "PENDING",
        "created_at": now_str()
    })
    
    # 4. Gửi thông báo đang xử lý
    await query.edit_message_text(
        f"⏳ *ĐANG XỬ LÝ...*\\n\\n"
        f"🧾 Mã đơn: `{order_id}`\\n"
        f"📦 SP: {product['name']}\\n"
        f"💰 Giá: {fmt_price(product['price'] * qty)}\\n\\n"
        f"🔄 Đang tự động thanh toán...\\n"
        f"⏱ Vui lòng đợi 30-60 giây...",
        parse_mode="Markdown"
    )
    
    # 5. Gọi auto payment
    try:
        result = await handle_order_with_auto_payment(
            order_id=order_id,
            product=ProductWithPayment(product),
            user_id=user_id,
            qty=qty
        )
        
        # 6. Xử lý kết quả
        if result['success']:
            # Payment thành công
            payment_result = result['payment_result']
            
            await query.edit_message_text(
                f"✅ *THANH TOÁN THÀNH CÔNG*\\n\\n"
                f"🧾 Mã đơn: `{order_id}`\\n"
                f"📦 SP: {product['name']}\\n"
                f"💰 Giá: {fmt_price(product['price'] * qty)}\\n\\n"
                f"💳 Thẻ: {payment_result['card_used']}\\n\\n"
                f"🎁 Đang giao hàng...",
                parse_mode="Markdown"
            )
            
            # Giao hàng
            items = await gs_call(mark_sold_and_get_secrets, order_id)
            
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
                    "✅ *ĐÃ GIAO HÀNG THÀNH CÔNG*\\n\\n"
                    "📄 Thông tin đã được gửi ở tin nhắn phía trên.",
                    parse_mode="Markdown",
                    reply_markup=kb_after_delivery()
                )
        else:
            # Payment thất bại - trả kho
            await gs_call(release_hold_by_order, order_id, "PAYMENT_FAILED")
            
            error = result.get('error', 'Unknown error')
            
            await query.edit_message_text(
                f"❌ *THANH TOÁN THẤT BẠI*\\n\\n"
                f"🧾 Mã đơn: `{order_id}`\\n"
                f"📦 SP: {product['name']}\\n\\n"
                f"⚠️ Lỗi: {error}\\n\\n"
                f"💬 Vui lòng liên hệ admin để được hỗ trợ.",
                parse_mode="Markdown",
                reply_markup=kb_support_only()
            )
            
    except Exception as e:
        logger.exception(f"Auto payment error: {e}")
        
        # Trả kho
        await gs_call(release_hold_by_order, order_id, "ERROR")
        
        await query.edit_message_text(
            f"❌ *LỖI HỆ THỐNG*\\n\\n"
            f"🧾 Mã đơn: `{order_id}`\\n\\n"
            f"⚠️ Đã xảy ra lỗi khi xử lý thanh toán.\\n"
            f"💬 Vui lòng liên hệ admin.",
            parse_mode="Markdown",
            reply_markup=kb_support_only()
        )


# ============= ADMIN COMMANDS =============

async def cmd_payment_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command /payment_stats"""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Không có quyền")
        return
    
    service = IntegratedPaymentService()
    stats = service.get_payment_stats()
    
    text = (
        "📊 *THỐNG KÊ THANH TOÁN*\\n\\n"
        f"💳 Thẻ active: {stats['active_cards']}\\n"
        f"✅ Thành công: {stats['success_transactions']}\\n"
        f"❌ Thất bại: {stats['failed_transactions']}\\n"
        f"📈 Tỷ lệ: {stats['success_rate']:.1f}%"
    )
    
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_list_cards(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command /list_cards"""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Không có quyền")
        return
    
    service = IntegratedPaymentService()
    cards = service.card_db.get_active_cards()
    
    if not cards:
        await update.message.reply_text("Không có thẻ nào")
        return
    
    text = f"💳 *DANH SÁCH THẺ* ({len(cards)} thẻ)\\n\\n"
    
    for card in cards[:10]:
        text += (
            f"🆔 ID: {card['id']}\\n"
            f"💳 Số: ****{card['card_number'][-4:]}\\n"
            f"👤 Tên: {card['card_holder']}\\n"
            f"✅ Thành công: {card['success_count']} | "
            f"❌ Thất bại: {card['fail_count']}\\n"
            f"⭐ Priority: {card['priority']}\\n"
            f"{'─' * 30}\\n"
        )
    
    await update.message.reply_text(text, parse_mode="Markdown")

# ================================================
'''
    
    # Thêm vào cuối file, trước hàm main()
    main_pattern = r'(def main\(\):)'
    
    if re.search(main_pattern, content):
        content = re.sub(main_pattern, handlers_code + r'\n\1', content)
        print("✓ Đã thêm payment handlers")
    else:
        print("⚠️  Không tìm thấy hàm main(), thêm vào cuối file")
        content += handlers_code
    
    return content


def add_command_handlers(content):
    """Thêm command handlers vào main()"""
    
    # Tìm hàm main()
    main_pattern = r'(def main\(\):.*?application\.run_polling)'
    
    match = re.search(main_pattern, content, re.DOTALL)
    
    if not match:
        print("⚠️  Không tìm thấy hàm main()")
        return content
    
    main_func = match.group(0)
    
    # Check xem đã có chưa
    if 'cmd_payment_stats' in main_func:
        print("⚠️  Command handlers đã được thêm, bỏ qua")
        return content
    
    # Thêm handlers
    new_handlers = """
    # ✅ Payment commands
    application.add_handler(CommandHandler("payment_stats", cmd_payment_stats))
    application.add_handler(CommandHandler("list_cards", cmd_list_cards))
    
    """
    
    # Thêm trước run_polling
    new_main = main_func.replace(
        'application.run_polling',
        new_handlers + '    application.run_polling'
    )
    
    content = content.replace(main_func, new_main)
    
    print("✓ Đã thêm command handlers")
    return content


def main():
    """Main function"""
    
    print("=" * 60)
    print("BOT_SHOP.PY AUTO PAYMENT PATCH")
    print("=" * 60)
    print()
    
    bot_shop_path = 'bot_shop.py'
    
    if not os.path.exists(bot_shop_path):
        print(f"❌ Không tìm thấy file: {bot_shop_path}")
        print("   Vui lòng chạy script này trong thư mục bottele/")
        return
    
    # Backup
    print("📦 Đang backup file...")
    if not backup_file(bot_shop_path):
        print("❌ Backup thất bại, dừng patch")
        return
    
    print()
    
    # Read file
    with open(bot_shop_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Apply patches
    print("🔧 Đang apply patches...")
    print()
    
    content = add_import_section(content)
    content = update_load_products(content)
    content = add_payment_handlers(content)
    content = add_command_handlers(content)
    
    # Write file
    print()
    print("💾 Đang lưu file...")
    
    with open(bot_shop_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✓ Đã lưu file")
    print()
    
    print("=" * 60)
    print("✅ PATCH HOÀN TẤT!")
    print("=" * 60)
    print()
    print("📝 Các bước tiếp theo:")
    print("   1. Kiểm tra file bot_shop.py")
    print("   2. Thêm thẻ test: python add_test_cards.py add")
    print("   3. Update Google Sheets (thêm cột payment)")
    print("   4. Chạy bot: python main.py")
    print()
    print("📄 File backup: bot_shop.py.backup")
    print("   (Nếu có lỗi, restore bằng: copy bot_shop.py.backup bot_shop.py)")
    print()


if __name__ == "__main__":
    main()
