"""
Test Google Sheets connection
"""

import os
from dotenv import load_dotenv
load_dotenv()

print("=" * 60)
print("TEST GOOGLE SHEETS CONNECTION")
print("=" * 60)
print()

# Test 1: Import
print("Test 1: Import modules...")
try:
    from bot_shop import (
        init_sheets,
        load_products,
        stock_count_ready_by_code,
        get_all_records,
        _ws_products,
        _ws_pool
    )
    print("✓ Import thành công")
except Exception as e:
    print(f"✗ Import thất bại: {e}")
    exit(1)

print()

# Test 2: Connection
print("Test 2: Kết nối Google Sheets...")
try:
    init_sheets()
    print("✓ Kết nối thành công")
except Exception as e:
    print(f"✗ Kết nối thất bại: {e}")
    print("\nKiểm tra:")
    print("  - GSHEET_ID trong .env")
    print("  - service_account.json tồn tại")
    print("  - Permissions của service account")
    exit(1)

print()

# Test 3: Load products
print("Test 3: Load products...")
try:
    products = load_products()
    print(f"✓ Load thành công: {len(products)} sản phẩm")
    print()
    
    if len(products) == 0:
        print("⚠️  Chưa có sản phẩm nào trong sheet PRODUCTS")
    else:
        print("Danh sách sản phẩm:")
        for i, p in enumerate(products[:5], 1):
            print(f"\n{i}. {p['product_id']}: {p['name']}")
            print(f"   Giá: {p['price']:,} đ")
            print(f"   Stock code: {p['stock_code']}")
            
            # Check payment fields
            if p.get('requires_payment'):
                print(f"   ✅ Cần payment:")
                print(f"      URL: {p.get('payment_url', 'N/A')}")
                print(f"      Email: {p.get('account_email', 'N/A')}")
            else:
                print(f"   ❌ Không cần payment")
        
        if len(products) > 5:
            print(f"\n... và {len(products) - 5} sản phẩm khác")
    
except Exception as e:
    print(f"✗ Load products thất bại: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print()
print("=" * 60)

# Test 4: Load stock
print("\nTest 4: Load stock...")
try:
    stock = stock_count_ready_by_code()
    print(f"✓ Load thành công: {len(stock)} stock codes")
    print()
    
    if len(stock) == 0:
        print("⚠️  Chưa có items READY nào trong sheet POOL")
    else:
        print("Stock hiện có:")
        for code, count in list(stock.items())[:10]:
            print(f"   - {code}: {count} items")
        
        if len(stock) > 10:
            print(f"   ... và {len(stock) - 10} stock codes khác")
    
except Exception as e:
    print(f"✗ Load stock thất bại: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 60)

# Test 5: Check payment fields
print("\nTest 5: Kiểm tra payment fields...")
try:
    products_with_payment = [p for p in products if p.get('requires_payment')]
    
    print(f"✓ Tìm thấy {len(products_with_payment)} sản phẩm cần payment")
    
    if len(products_with_payment) > 0:
        print("\nSản phẩm cần payment:")
        for p in products_with_payment[:3]:
            print(f"\n   {p['product_id']}: {p['name']}")
            
            # Validate fields
            issues = []
            if not p.get('payment_url'):
                issues.append("Thiếu payment_url")
            if not p.get('account_email'):
                issues.append("Thiếu account_email")
            if not p.get('account_password'):
                issues.append("Thiếu account_password")
            
            if issues:
                print(f"   ⚠️  Issues: {', '.join(issues)}")
            else:
                print(f"   ✓ Đầy đủ thông tin payment")
    else:
        print("\n⚠️  Chưa có sản phẩm nào cần payment")
        print("   Để test auto payment, thêm product với:")
        print("   - requires_payment = yes")
        print("   - payment_url = URL thanh toán")
        print("   - account_email = email account")
        print("   - account_password = password")
    
except Exception as e:
    print(f"✗ Check payment fields thất bại: {e}")

print()
print("=" * 60)
print()

# Summary
print("📊 SUMMARY:")
print(f"   ✓ Connection: OK")
print(f"   ✓ Products: {len(products)}")
print(f"   ✓ Stock codes: {len(stock)}")
print(f"   ✓ Products with payment: {len(products_with_payment)}")
print()

if len(products) > 0 and len(stock) > 0:
    print("✅ TẤT CẢ TESTS ĐỀU PASS!")
    print()
    print("📝 Bước tiếp theo:")
    print("   1. Thêm thẻ test: python add_test_cards.py add")
    print("   2. Test bot: python main.py")
else:
    print("⚠️  CẦN THÊM DATA:")
    if len(products) == 0:
        print("   - Thêm products vào sheet PRODUCTS")
    if len(stock) == 0:
        print("   - Thêm items vào sheet POOL")

print()
