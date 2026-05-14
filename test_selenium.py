"""
Test Selenium browser automation
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'pay_kiro'))

print("=" * 60)
print("TEST SELENIUM BROWSER AUTOMATION")
print("=" * 60)
print()

print("Test 1: Import modules...")
try:
    from payment_automation import KiroPaymentAutomation
    print("✓ Import thành công")
except Exception as e:
    print(f"✗ Import thất bại: {e}")
    print("\nKiểm tra:")
    print("  - Đã cài selenium: pip install selenium")
    print("  - Đã cài webdriver-manager: pip install webdriver-manager")
    exit(1)

print()

# Test với URL đơn giản
print("Test 2: Khởi tạo automation...")
automation = KiroPaymentAutomation(
    email="test@example.com",
    password="test123",
    payment_url="https://www.google.com",
    headless=False  # Để xem browser
)
print("✓ Automation initialized")

print()

try:
    print("Test 3: Khởi tạo WebDriver...")
    print("   (Browser Chrome sẽ mở...)")
    automation.init_driver()
    print("✓ Driver initialized")
    
    print()
    print("Test 4: Navigate to Google...")
    automation.driver.get("https://www.google.com")
    print("✓ Navigate OK")
    
    print()
    print("Test 5: Get page title...")
    title = automation.driver.title
    print(f"✓ Page title: {title}")
    
    print()
    print("Test 6: Take screenshot...")
    screenshot = automation.take_screenshot("test_google")
    print(f"✓ Screenshot saved: {screenshot}")
    
    print()
    print("Test 7: Navigate to another page...")
    automation.driver.get("https://httpbin.org/delay/1")
    print("✓ Navigate OK")
    
    print()
    print("Test 8: Take another screenshot...")
    screenshot2 = automation.take_screenshot("test_httpbin")
    print(f"✓ Screenshot saved: {screenshot2}")
    
    print()
    print("=" * 60)
    print()
    print("✅ TẤT CẢ TESTS ĐỀU PASS!")
    print()
    print("Browser đang mở, bạn có thể:")
    print("  - Xem browser")
    print("  - Check screenshots trong thư mục screenshots/")
    print()
    
    input("Nhấn Enter để đóng browser...")
    
    print()
    print("Test 9: Close driver...")
    automation.close_driver()
    print("✓ Driver closed")
    
    print()
    print("=" * 60)
    print()
    print("🎉 SELENIUM TEST HOÀN TẤT!")
    print()
    print("📝 Bước tiếp theo:")
    print("   1. Check screenshots: dir screenshots")
    print("   2. Test với payment URL thật")
    print("   3. Test bot: python main.py")
    print()
    
except Exception as e:
    print(f"\n✗ Test thất bại: {e}")
    print()
    print("Debug:")
    print("  - Check Chrome đã cài chưa")
    print("  - Check ChromeDriver version")
    print("  - Check network connection")
    print()
    
    import traceback
    traceback.print_exc()
    
    try:
        automation.close_driver()
    except:
        pass
    
    exit(1)
