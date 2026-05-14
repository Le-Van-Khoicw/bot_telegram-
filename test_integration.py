"""
Test script để verify tích hợp auto payment
Chạy: python test_integration.py
"""

import sys
import os
import asyncio

# Add pay_kiro to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'pay_kiro'))


def test_imports():
    """Test 1: Kiểm tra imports"""
    print("=" * 60)
    print("TEST 1: KIỂM TRA IMPORTS")
    print("=" * 60)
    
    try:
        from database import CardDatabase
        print("✓ Import CardDatabase thành công")
    except Exception as e:
        print(f"✗ Import CardDatabase thất bại: {e}")
        return False
    
    try:
        from payment_automation import KiroPaymentAutomation
        print("✓ Import KiroPaymentAutomation thành công")
    except Exception as e:
        print(f"✗ Import KiroPaymentAutomation thất bại: {e}")
        return False
    
    try:
        from integrated_payment import (
            IntegratedPaymentService,
            ProductWithPayment,
            handle_order_with_auto_payment
        )
        print("✓ Import integrated_payment thành công")
    except Exception as e:
        print(f"✗ Import integrated_payment thất bại: {e}")
        return False
    
    print()
    return True


def test_database():
    """Test 2: Kiểm tra database"""
    print("=" * 60)
    print("TEST 2: KIỂM TRA DATABASE")
    print("=" * 60)
    
    try:
        from database import CardDatabase
        
        db = CardDatabase()
        print("✓ Kết nối database thành công")
        
        # Check cards
        cards = db.get_active_cards()
        print(f"✓ Tìm thấy {len(cards)} thẻ active")
        
        if len(cards) == 0:
            print("⚠️  Chưa có thẻ nào! Chạy: python add_test_cards.py add")
        else:
            for card in cards[:3]:
                print(f"   - ID {card['id']}: ****{card['card_number'][-4:]} (Priority: {card['priority']})")
        
        # Check stats
        stats = db.get_stats()
        print(f"✓ Stats: {stats['active_cards']} thẻ, "
              f"{stats['success_transactions']} thành công, "
              f"{stats['failed_transactions']} thất bại")
        
        print()
        return True
        
    except Exception as e:
        print(f"✗ Database error: {e}")
        print()
        return False


def test_payment_service():
    """Test 3: Kiểm tra payment service"""
    print("=" * 60)
    print("TEST 3: KIỂM TRA PAYMENT SERVICE")
    print("=" * 60)
    
    try:
        from integrated_payment import IntegratedPaymentService
        
        service = IntegratedPaymentService()
        print("✓ Khởi tạo IntegratedPaymentService thành công")
        
        # Get stats
        stats = service.get_payment_stats()
        print(f"✓ Get stats thành công:")
        print(f"   - Thẻ active: {stats['active_cards']}")
        print(f"   - Success rate: {stats['success_rate']:.1f}%")
        
        print()
        return True
        
    except Exception as e:
        print(f"✗ Payment service error: {e}")
        print()
        return False


def test_product_model():
    """Test 4: Kiểm tra ProductWithPayment model"""
    print("=" * 60)
    print("TEST 4: KIỂM TRA PRODUCT MODEL")
    print("=" * 60)
    
    try:
        from integrated_payment import ProductWithPayment
        
        # Test data
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
        print("✓ Tạo ProductWithPayment thành công")
        print(f"   - Product ID: {product.product_id}")
        print(f"   - Name: {product.name}")
        print(f"   - Requires payment: {product.requires_payment}")
        print(f"   - Payment URL: {product.payment_url}")
        
        print()
        return True
        
    except Exception as e:
        print(f"✗ Product model error: {e}")
        print()
        return False


def test_env_config():
    """Test 5: Kiểm tra environment config"""
    print("=" * 60)
    print("TEST 5: KIỂM TRA ENV CONFIG")
    print("=" * 60)
    
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = [
        'BOT_TOKEN',
        'GSHEET_ID',
        'GSVC_JSON'
    ]
    
    optional_vars = [
        'PAYMENT_HEADLESS',
        'MAX_RETRY_CARDS',
        'PAYMENT_TIMEOUT'
    ]
    
    all_ok = True
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"✓ {var}: {'*' * 10} (set)")
        else:
            print(f"✗ {var}: NOT SET")
            all_ok = False
    
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            print(f"✓ {var}: {value}")
        else:
            print(f"⚠️  {var}: not set (sẽ dùng default)")
    
    print()
    return all_ok


async def test_async_payment():
    """Test 6: Test async payment (mock)"""
    print("=" * 60)
    print("TEST 6: TEST ASYNC PAYMENT (MOCK)")
    print("=" * 60)
    
    try:
        from integrated_payment import ProductWithPayment
        
        # Mock product
        test_product = {
            'product_id': 'TEST_MOCK',
            'name': 'Mock Product',
            'price': 50000,
            'stock_code': 'MOCK_POOL',
            'requires_payment': 'yes',
            'payment_url': 'https://httpbin.org/delay/2',  # Mock URL
            'payment_provider': 'custom',
            'account_email': 'mock@example.com',
            'account_password': 'mock123'
        }
        
        product = ProductWithPayment(test_product)
        print("✓ Tạo mock product thành công")
        
        # Note: Không chạy thật vì cần browser
        print("⚠️  Bỏ qua test thực tế (cần browser)")
        print("   Để test thực tế, chạy bot và mua product")
        
        print()
        return True
        
    except Exception as e:
        print(f"✗ Async payment test error: {e}")
        print()
        return False


def test_file_structure():
    """Test 7: Kiểm tra cấu trúc file"""
    print("=" * 60)
    print("TEST 7: KIỂM TRA CẤU TRÚC FILE")
    print("=" * 60)
    
    required_files = [
        'integrated_payment.py',
        'add_test_cards.py',
        'bot_shop_payment_patch.py',
        'INTEGRATION_GUIDE.md',
        'QUICK_START_PAYMENT.md',
        'test_integration.py'
    ]
    
    pay_kiro_files = [
        '../pay_kiro/database.py',
        '../pay_kiro/payment_automation.py'
    ]
    
    all_ok = True
    
    for file in required_files:
        if os.path.exists(file):
            print(f"✓ {file}")
        else:
            print(f"✗ {file} - NOT FOUND")
            all_ok = False
    
    for file in pay_kiro_files:
        if os.path.exists(file):
            print(f"✓ {file}")
        else:
            print(f"✗ {file} - NOT FOUND")
            all_ok = False
    
    print()
    return all_ok


def main():
    """Main test function"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "AUTO PAYMENT INTEGRATION TEST" + " " * 18 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    results = []
    
    # Run tests
    results.append(("Imports", test_imports()))
    results.append(("Database", test_database()))
    results.append(("Payment Service", test_payment_service()))
    results.append(("Product Model", test_product_model()))
    results.append(("Env Config", test_env_config()))
    results.append(("File Structure", test_file_structure()))
    
    # Async test
    try:
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(test_async_payment())
        results.append(("Async Payment", result))
    except Exception as e:
        print(f"✗ Async test error: {e}")
        results.append(("Async Payment", False))
    
    # Summary
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:10} - {name}")
    
    print()
    print(f"Kết quả: {passed}/{total} tests passed")
    
    if passed == total:
        print()
        print("🎉 TẤT CẢ TESTS ĐỀU PASS!")
        print()
        print("📝 Các bước tiếp theo:")
        print("   1. Thêm thẻ test: python add_test_cards.py add")
        print("   2. Patch bot_shop.py: python bot_shop_payment_patch.py")
        print("   3. Update Google Sheets (thêm cột payment)")
        print("   4. Chạy bot: python main.py")
        print()
    else:
        print()
        print("⚠️  MỘT SỐ TESTS THẤT BẠI")
        print()
        print("Vui lòng kiểm tra lại:")
        for name, result in results:
            if not result:
                print(f"   - {name}")
        print()
    
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
