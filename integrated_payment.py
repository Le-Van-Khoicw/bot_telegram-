"""
Tích hợp Auto Payment vào Shop Bot
Tự động thanh toán khi user mua account
"""

import os
import asyncio
import logging
from typing import Dict, Optional, List
from datetime import datetime
from enum import Enum

# Import từ pay_kiro
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'pay_kiro'))

from database import CardDatabase
from payment_automation import KiroPaymentAutomation


logger = logging.getLogger(__name__)


class PaymentProvider(Enum):
    """Các nhà cung cấp payment"""
    KIRO = "kiro"
    STRIPE = "stripe"
    PAYPAL = "paypal"
    CUSTOM = "custom"


class IntegratedPaymentService:
    """
    Service tích hợp auto payment vào shop bot
    
    Flow:
    1. User mua product có payment_link
    2. Bot tạo order và gọi service này
    3. Service tự động thanh toán bằng thẻ
    4. Trả về kết quả để bot giao hàng
    """
    
    def __init__(self):
        self.card_db = CardDatabase()
        self.logger = logging.getLogger(__name__)
        
        # Config
        self.headless = os.getenv('PAYMENT_HEADLESS', 'True').lower() == 'true'
        self.max_retry_cards = int(os.getenv('MAX_RETRY_CARDS', '3'))
    
    async def auto_pay_for_order(
        self,
        order_id: str,
        payment_url: str,
        amount: float,
        account_email: str,
        account_password: str,
        provider: PaymentProvider = PaymentProvider.CUSTOM
    ) -> Dict:
        """
        Tự động thanh toán cho order
        
        Args:
            order_id: ID đơn hàng
            payment_url: Link thanh toán
            amount: Số tiền
            account_email: Email account cần thanh toán
            account_password: Password account
            provider: Nhà cung cấp payment
        
        Returns:
            {
                "success": bool,
                "order_id": str,
                "card_used": str,
                "transaction_id": str,
                "error": str (nếu có)
            }
        """
        self.logger.info(f"Starting auto payment for order {order_id}")
        
        try:
            # 1. Lấy danh sách thẻ active
            cards = self.card_db.get_active_cards()
            
            if not cards:
                return {
                    "success": False,
                    "order_id": order_id,
                    "error": "No active cards available"
                }
            
            # 2. Giới hạn số thẻ thử
            cards_to_try = cards[:self.max_retry_cards]
            
            self.logger.info(f"Found {len(cards)} cards, will try {len(cards_to_try)}")
            
            # 3. Khởi tạo automation
            automation = KiroPaymentAutomation(
                email=account_email,
                password=account_password,
                payment_url=payment_url,
                headless=self.headless
            )
            
            # 4. Thử thanh toán với từng thẻ
            result = await self._try_payment_with_cards(
                automation,
                cards_to_try,
                order_id
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Auto payment failed for order {order_id}: {e}")
            return {
                "success": False,
                "order_id": order_id,
                "error": str(e)
            }
    
    async def _try_payment_with_cards(
        self,
        automation: KiroPaymentAutomation,
        cards: List[Dict],
        order_id: str
    ) -> Dict:
        """Thử thanh toán với danh sách thẻ"""
        
        # Init driver
        await asyncio.to_thread(automation.init_driver)
        
        try:
            # Navigate to payment page
            if not await asyncio.to_thread(automation.navigate_to_payment):
                return {
                    "success": False,
                    "order_id": order_id,
                    "error": "Failed to navigate to payment page"
                }
            
            # Thử từng thẻ
            for i, card in enumerate(cards, 1):
                self.logger.info(
                    f"Trying card {i}/{len(cards)}: ****{card['card_number'][-4:]}"
                )
                
                success, error_msg = await asyncio.to_thread(
                    automation.process_payment_with_card,
                    card
                )
                
                if success:
                    self.logger.info(f"Payment successful with card {card['id']}")
                    
                    return {
                        "success": True,
                        "order_id": order_id,
                        "card_used": f"****{card['card_number'][-4:]}",
                        "card_id": card['id'],
                        "transaction_id": f"TXN_{order_id}_{int(datetime.now().timestamp())}"
                    }
                else:
                    self.logger.warning(
                        f"Card {card['id']} failed: {error_msg}"
                    )
                    
                    # Reload page để thử thẻ tiếp theo
                    if i < len(cards):
                        await asyncio.to_thread(automation.navigate_to_payment)
                        await asyncio.sleep(2)
            
            # Tất cả thẻ đều fail
            return {
                "success": False,
                "order_id": order_id,
                "error": "All cards failed"
            }
            
        finally:
            # Đóng driver
            await asyncio.to_thread(automation.close_driver)
    
    def get_payment_stats(self) -> Dict:
        """Lấy thống kê thanh toán"""
        stats = self.card_db.get_stats()
        
        return {
            "active_cards": stats['active_cards'],
            "success_transactions": stats['success_transactions'],
            "failed_transactions": stats['failed_transactions'],
            "success_rate": (
                stats['success_transactions'] / 
                (stats['success_transactions'] + stats['failed_transactions'])
                * 100
            ) if (stats['success_transactions'] + stats['failed_transactions']) > 0 else 0
        }


# ============= INTEGRATION VỚI BOT_SHOP.PY =============

class ProductWithPayment:
    """
    Model cho product có payment link
    Thêm vào PRODUCTS sheet
    """
    
    def __init__(self, row: Dict):
        self.product_id = row.get('product_id')
        self.name = row.get('name')
        self.price = int(row.get('price', 0))
        self.stock_code = row.get('stock_code')
        self.description = row.get('description', '')
        
        # ✅ Thêm fields mới
        self.requires_payment = row.get('requires_payment', 'no').lower() == 'yes'
        self.payment_url = row.get('payment_url', '')
        self.payment_provider = row.get('payment_provider', 'custom')
        self.account_email = row.get('account_email', '')
        self.account_password = row.get('account_password', '')


async def handle_order_with_auto_payment(
    order_id: str,
    product: ProductWithPayment,
    user_id: int,
    qty: int
) -> Dict:
    """
    Xử lý order có auto payment
    
    Flow:
    1. Kiểm tra product có requires_payment không
    2. Nếu có → gọi auto payment
    3. Nếu payment thành công → giao hàng
    4. Nếu payment thất bại → thông báo user
    
    Returns:
        {
            "success": bool,
            "order_id": str,
            "payment_result": dict,
            "delivery_result": dict
        }
    """
    
    logger.info(f"Processing order {order_id} for product {product.product_id}")
    
    # 1. Kiểm tra có cần auto payment không
    if not product.requires_payment:
        logger.info(f"Product {product.product_id} doesn't require payment")
        return {
            "success": True,
            "order_id": order_id,
            "requires_payment": False,
            "message": "No payment required"
        }
    
    # 2. Validate payment info
    if not product.payment_url:
        return {
            "success": False,
            "order_id": order_id,
            "error": "Missing payment_url"
        }
    
    if not product.account_email or not product.account_password:
        return {
            "success": False,
            "order_id": order_id,
            "error": "Missing account credentials"
        }
    
    # 3. Gọi auto payment service
    payment_service = IntegratedPaymentService()
    
    payment_result = await payment_service.auto_pay_for_order(
        order_id=order_id,
        payment_url=product.payment_url,
        amount=product.price * qty,
        account_email=product.account_email,
        account_password=product.account_password,
        provider=PaymentProvider(product.payment_provider)
    )
    
    # 4. Xử lý kết quả
    if payment_result['success']:
        logger.info(f"Payment successful for order {order_id}")
        
        # TODO: Gọi hàm giao hàng từ bot_shop.py
        # delivery_result = await deliver_order(order_id)
        
        return {
            "success": True,
            "order_id": order_id,
            "requires_payment": True,
            "payment_result": payment_result,
            "message": "Payment successful, order will be delivered"
        }
    else:
        logger.error(f"Payment failed for order {order_id}: {payment_result.get('error')}")
        
        return {
            "success": False,
            "order_id": order_id,
            "requires_payment": True,
            "payment_result": payment_result,
            "error": payment_result.get('error', 'Payment failed')
        }


# ============= TELEGRAM BOT HANDLERS =============

async def handle_buy_with_payment(update, context, product: ProductWithPayment):
    """
    Handler cho nút mua product có payment
    Tích hợp vào bot_shop.py
    """
    user_id = update.effective_user.id
    
    # 1. Tạo order_id
    order_id = generate_order_id()
    
    # 2. Gửi thông báo đang xử lý
    processing_msg = await update.message.reply_text(
        f"⏳ *Đang xử lý đơn hàng...*\n\n"
        f"🧾 Mã đơn: `{order_id}`\n"
        f"📦 Sản phẩm: {product.name}\n"
        f"💰 Giá: {fmt_price(product.price)}\n\n"
        f"🔄 Đang tự động thanh toán...",
        parse_mode="Markdown"
    )
    
    # 3. Xử lý order với auto payment
    result = await handle_order_with_auto_payment(
        order_id=order_id,
        product=product,
        user_id=user_id,
        qty=1
    )
    
    # 4. Cập nhật message
    if result['success']:
        await processing_msg.edit_text(
            f"✅ *THANH TOÁN THÀNH CÔNG*\n\n"
            f"🧾 Mã đơn: `{order_id}`\n"
            f"📦 Sản phẩm: {product.name}\n"
            f"💰 Giá: {fmt_price(product.price)}\n\n"
            f"💳 Thẻ sử dụng: {result['payment_result']['card_used']}\n\n"
            f"🎁 Đang giao hàng tự động...",
            parse_mode="Markdown"
        )
        
        # TODO: Giao hàng
        
    else:
        await processing_msg.edit_text(
            f"❌ *THANH TOÁN THẤT BẠI*\n\n"
            f"🧾 Mã đơn: `{order_id}`\n"
            f"📦 Sản phẩm: {product.name}\n\n"
            f"⚠️ Lỗi: {result.get('error', 'Unknown error')}\n\n"
            f"💬 Vui lòng liên hệ admin để được hỗ trợ.",
            parse_mode="Markdown"
        )


# ============= HELPER FUNCTIONS =============

def generate_order_id() -> str:
    """Generate order ID"""
    import random
    import string
    from datetime import datetime
    
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}{suffix}"


def fmt_price(vnd: int) -> str:
    """Format price"""
    return f"{vnd:,} đ".replace(",", ".")


# ============= ADMIN COMMANDS =============

async def cmd_payment_stats(update, context):
    """
    Command /payment_stats - Xem thống kê payment
    Chỉ admin
    """
    user_id = update.effective_user.id
    
    # Check admin
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Bạn không có quyền sử dụng lệnh này")
        return
    
    service = IntegratedPaymentService()
    stats = service.get_payment_stats()
    
    text = (
        "📊 *THỐNG KÊ THANH TOÁN*\n\n"
        f"💳 Thẻ active: {stats['active_cards']}\n"
        f"✅ Giao dịch thành công: {stats['success_transactions']}\n"
        f"❌ Giao dịch thất bại: {stats['failed_transactions']}\n"
        f"📈 Tỷ lệ thành công: {stats['success_rate']:.1f}%"
    )
    
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_add_payment_card(update, context):
    """
    Command /add_card - Thêm thẻ thanh toán
    Chỉ admin
    """
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Bạn không có quyền sử dụng lệnh này")
        return
    
    # TODO: Implement interactive card adding
    await update.message.reply_text(
        "💳 *THÊM THẺ THANH TOÁN*\n\n"
        "Vui lòng gửi thông tin thẻ theo format:\n\n"
        "`/add_card_confirm`\n"
        "`Số thẻ: 4154620022238586`\n"
        "`Tên: NGUYEN VAN A`\n"
        "`Hết hạn: 12/29`\n"
        "`CVV: 123`\n"
        "`Priority: 1`",
        parse_mode="Markdown"
    )


# ============= USAGE EXAMPLE =============

if __name__ == "__main__":
    """
    Example usage
    """
    
    # 1. Tạo product có payment
    product = ProductWithPayment({
        'product_id': 'KIRO_PRO',
        'name': 'Kiro Pro 1 Month',
        'price': 350000,
        'stock_code': 'KIRO_ACCOUNTS',
        'requires_payment': 'yes',
        'payment_url': 'https://kiro.ai/payment',
        'payment_provider': 'custom',
        'account_email': 'user@example.com',
        'account_password': 'password123'
    })
    
    # 2. Xử lý order
    async def test():
        result = await handle_order_with_auto_payment(
            order_id='ORD20260510120000ABCD',
            product=product,
            user_id=123456789,
            qty=1
        )
        
        print(result)
    
    asyncio.run(test())
