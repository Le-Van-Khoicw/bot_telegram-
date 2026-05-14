"""
Test bot commands (không cần Telegram user)
"""

import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'pay_kiro'))

print("=" * 60)
print("TEST BOT COMMANDS")
print("=" * 60)
print()

async def test_commands():
    # Test 1: Import
    print("Test 1: Import modules...")
    try:
        from integrated_payment import IntegratedPaymentService, ProductWithPayment
        from database import CardDatabase
        print("✓ Import thành công")
    except Exception as e:
        print(f"✗ Import thất bại: {e}")
        return False
    
    print()
    
    # Test 2: Initialize service
    print("Test 2: Initialize IntegratedPaymentService...")
    try:
        service = IntegratedPaymentService()
        print("✓ Service initialized")
    except Exception as e:
        print(f"✗ Initialize thất bại: {e}")
        return False
    
    print()
    
    # Test 3: Get payment stats
    print("Test 3: Get payment stats...")
    try:
        stats = service.get_payment_stats()
        print("✓ Stats retrieved:")
        print(f"   - Active cards: {stats['active_cards']}")
        print(f"   - Success transactions: {stats['success_transactions']}")
        print(f"   - Failed transactions: {stats['failed_transactions']}")
        print(f"   - Success rate: {stats['success_rate']:.1f}%")
        
        if stats['active_cards'] == 0:
            print()
            print("⚠️  Chưa có thẻ nào!")
            print("   Chạy: python add_test_cards.py add")
    except Exception as e:
        print(f"✗ Get stats thất bại: {e}")
        return False
    
    print()
    
    # Test 4: Get cards
    print("Test 4: Get cards from database...")
    try:
        cards = service.card_db.get_active_cards()
        print(f"✓ Found {len(cards)} cards:")
        
        if len(cards) == 0:
            print("   (Chưa có thẻ nào)")
        else:
            for i, card in enumerate(cards[:5], 1):
                print(f"\n   {i}. ID {card['id']}: ****{card['card_number'][-4:]}")
                print(f"      Chủ thẻ: {card['card_holder']}")
                print(f"      Priority: {card['priority']}")
                print(f"      Success: {card['success_count']} | Fail: {card['fail_count']}")
                print(f"      Status: {card['status']}")
            
            if len(cards) > 5:
                print(f"\n   ... và {len(cards) - 5} thẻ khác")
    except Exception as e:
        print(f"✗ Get cards thất bại: {e}")
        return False
    
    print()
    
    # Test 5: Test ProductWithPayment model
    print("Test 5: Test ProductWithPayment model...")
    try:
        test_product = {
            'product_id': 'TEST_001',
            'name': 'Test Product',
            'price': 100000,
            'stock_code': 'TEST_POOL',
            'description': 'Test description',
            'requires_payment': 'yes',
            'payment_url': 'https://example.com/payment',
            'payment_provider': 'custom',
            'account_email': 'test@example.com',
            'account_password': 'password123'
        }
        
        product = ProductWithPayment(test_product)
        print("✓ ProductWithPayment created:")
        print(f"   - Product ID: {product.product_id}")
        print(f"   - Name: {product.name}")
        print(f"   - Price: {product.price:,} đ")
        print(f"   - Requires payment: {product.requires_payment}")
        print(f"   - Payment URL: {product.payment_url}")
        print(f"   - Account email: {product.account_email}")
    except Exception as e:
        print(f"✗ ProductWithPayment thất bại: {e}")
        return False
    
    print()
    
    # Test 6: Test database operations
    print("Test 6: Test database operations...")
    try:
        db = CardDatabase()
        
        # Get transaction history
        transactions = db.get_transaction_history(5)
        print(f"✓ Transaction history: {len(transactions)} giao dịch gần nhất")
        
        if len(transactions) > 0:
            for i, tx in enumerate(transactions, 1):
                print(f"\n   {i}. [{tx['transaction_date']}]")
                print(f"      Status: {tx['status']}")
                print(f"      Amount: {tx['amount']}")
                if tx.get('card_number'):
                    print(f"      Card: ****{tx['card_number'][-4:]}")
        else:
            print("   (Chưa có giao dịch nào)")
    except Exception as e:
        print(f"✗ Database operations thất bại: {e}")
        return False
    
    print()
    print("=" * 60)
    print()
    
    return True

# Run tests
async def main():
    success = await test_commands()
    
    if success:
        print("✅ TẤT CẢ TESTS ĐỀU PASS!")
        print()
        print("📝 Bước tiếp theo:")
        print("   1. Test Google Sheets: python test_sheets.py")
        print("   2. Test Selenium: python test_selenium.py")
        print("   3. Chạy bot: python main.py")
        print()
    else:
        print("✗ MỘT SỐ TESTS THẤT BẠI")
        print()
        print("Kiểm tra lại:")
        print("   - Dependencies đã cài đủ chưa")
        print("   - Database cards.db tồn tại chưa")
        print("   - Đã thêm thẻ test chưa")
        print()

asyncio.run(main())
