"""
Chạy tất cả tests local
"""

import subprocess
import sys
import os

def run_test(name, script):
    """Chạy một test script"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + f" {name}".ljust(58) + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    try:
        result = subprocess.run(
            [sys.executable, script],
            capture_output=False,
            text=True,
            cwd=os.path.dirname(__file__)
        )
        
        return result.returncode == 0
    except Exception as e:
        print(f"✗ Lỗi khi chạy {script}: {e}")
        return False

def main():
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 15 + "RUN ALL TESTS" + " " * 30 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    tests = [
        ("Test 1: Integration Test", "test_integration.py"),
        ("Test 2: Bot Commands", "test_bot_commands.py"),
        ("Test 3: Google Sheets", "test_sheets.py"),
        ("Test 4: Selenium", "test_selenium.py"),
    ]
    
    results = []
    
    for name, script in tests:
        if not os.path.exists(script):
            print(f"⚠️  Bỏ qua {name}: File {script} không tồn tại")
            results.append((name, None))
            continue
        
        success = run_test(name, script)
        results.append((name, success))
        
        if not success:
            print(f"\n⚠️  {name} thất bại!")
            response = input("Tiếp tục? (y/n): ")
            if response.lower() != 'y':
                break
    
    # Summary
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 20 + "SUMMARY" + " " * 31 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    passed = sum(1 for _, result in results if result is True)
    failed = sum(1 for _, result in results if result is False)
    skipped = sum(1 for _, result in results if result is None)
    total = len(results)
    
    for name, result in results:
        if result is True:
            status = "✓ PASS"
        elif result is False:
            status = "✗ FAIL"
        else:
            status = "⊘ SKIP"
        
        print(f"{status:10} - {name}")
    
    print()
    print(f"Kết quả: {passed} passed, {failed} failed, {skipped} skipped / {total} total")
    print()
    
    if passed == total:
        print("🎉 TẤT CẢ TESTS ĐỀU PASS!")
        print()
        print("📝 Bước tiếp theo:")
        print("   1. Patch bot_shop.py: python bot_shop_payment_patch.py")
        print("   2. Update Google Sheets (thêm cột payment)")
        print("   3. Chạy bot: python main.py")
        print("   4. Test mua hàng trên Telegram")
        print()
    elif failed == 0 and skipped > 0:
        print("⚠️  Một số tests bị skip")
        print()
    else:
        print("⚠️  MỘT SỐ TESTS THẤT BẠI")
        print()
        print("Kiểm tra lại:")
        for name, result in results:
            if result is False:
                print(f"   - {name}")
        print()

if __name__ == "__main__":
    main()
