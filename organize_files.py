"""
Script tự động tổ chức lại files
Chạy: python organize_files.py
"""

import os
import shutil

def create_directories():
    """Tạo các thư mục cần thiết"""
    dirs = ['payment', 'scripts', 'tests', 'docs']
    
    print("Tạo thư mục...")
    for d in dirs:
        if not os.path.exists(d):
            os.makedirs(d)
            print(f"  ✓ Tạo {d}/")
        else:
            print(f"  ⊙ {d}/ đã tồn tại")
    print()

def move_files():
    """Di chuyển files vào thư mục tương ứng"""
    
    moves = {
        # Payment files
        'integrated_payment.py': 'payment/service.py',
        
        # Scripts
        'add_test_cards.py': 'scripts/add_cards.py',
        'bot_shop_payment_patch.py': 'scripts/patch_bot.py',
        'run_all_tests.py': 'scripts/test_all.py',
        
        # Tests
        'test_integration.py': 'tests/test_integration.py',
        'test_bot_commands.py': 'tests/test_commands.py',
        'test_sheets.py': 'tests/test_sheets.py',
        'test_selenium.py': 'tests/test_selenium.py',
        
        # Docs
        'START_HERE.md': 'docs/01_START_HERE.md',
        'QUICK_START_PAYMENT.md': 'docs/02_QUICK_START.md',
        'INTEGRATION_GUIDE.md': 'docs/03_INTEGRATION.md',
        'LOCAL_TEST_GUIDE.md': 'docs/04_TEST_GUIDE.md',
        'SUMMARY.md': 'docs/05_SUMMARY.md',
        'README_PAYMENT_INTEGRATION.md': 'docs/06_REFERENCE.md',
        'README_TEST_LOCAL.md': 'docs/07_TEST_LOCAL.md',
    }
    
    print("Di chuyển files...")
    moved = 0
    skipped = 0
    
    for src, dst in moves.items():
        if os.path.exists(src):
            if os.path.exists(dst):
                print(f"  ⊙ {dst} đã tồn tại, bỏ qua")
                skipped += 1
            else:
                shutil.move(src, dst)
                print(f"  ✓ {src} → {dst}")
                moved += 1
        else:
            print(f"  ✗ {src} không tồn tại")
    
    print()
    print(f"Đã di chuyển: {moved} files")
    print(f"Bỏ qua: {skipped} files")
    print()

def create_init_files():
    """Tạo __init__.py cho packages"""
    
    print("Tạo __init__.py...")
    
    # payment/__init__.py
    payment_init = '''"""
Payment module - Auto payment integration
"""

from .service import IntegratedPaymentService, ProductWithPayment

__all__ = ['IntegratedPaymentService', 'ProductWithPayment']
'''
    
    with open('payment/__init__.py', 'w', encoding='utf-8') as f:
        f.write(payment_init)
    print("  ✓ payment/__init__.py")
    
    # scripts/__init__.py (empty)
    with open('scripts/__init__.py', 'w', encoding='utf-8') as f:
        f.write('# Scripts package\n')
    print("  ✓ scripts/__init__.py")
    
    # tests/__init__.py (empty)
    with open('tests/__init__.py', 'w', encoding='utf-8') as f:
        f.write('# Tests package\n')
    print("  ✓ tests/__init__.py")
    
    print()

def create_readme():
    """Tạo README.md mới"""
    
    readme = '''# 🤖 Shop Bot với Auto Payment

## 📁 Cấu trúc

```
bottele/
├── core/           # Code chính
├── payment/        # Auto payment module
├── scripts/        # Helper scripts
├── tests/          # Test suite
├── docs/           # Documentation
└── main.py         # Entry point
```

## 🚀 Quick Start

### 1. Cài đặt
```bash
pip install -r requirements.txt
```

### 2. Cấu hình
Copy `.env.example` thành `.env` và điền thông tin

### 3. Thêm thẻ test
```bash
python scripts/add_cards.py add
```

### 4. Chạy tests
```bash
python scripts/test_all.py
```

### 5. Chạy bot
```bash
python main.py
```

## 📚 Documentation

Đọc theo thứ tự:
1. `docs/01_START_HERE.md` - Bắt đầu
2. `docs/02_QUICK_START.md` - Quick start
3. `docs/03_INTEGRATION.md` - Integration guide
4. `docs/04_TEST_GUIDE.md` - Test guide

## 🧪 Testing

```bash
# Chạy tất cả tests
python scripts/test_all.py

# Test riêng lẻ
python tests/test_integration.py
python tests/test_commands.py
python tests/test_sheets.py
python tests/test_selenium.py
```

## 🔧 Scripts

```bash
# Thêm thẻ
python scripts/add_cards.py add

# Xem thẻ
python scripts/add_cards.py list

# Patch bot
python scripts/patch_bot.py
```

## 📞 Support

Xem docs/ để biết thêm chi tiết!
'''
    
    with open('README.md', 'w', encoding='utf-8') as f:
        f.write(readme)
    
    print("Tạo README.md...")
    print("  ✓ README.md")
    print()

def show_summary():
    """Hiển thị tổng kết"""
    
    print("=" * 60)
    print("TỔNG KẾT")
    print("=" * 60)
    print()
    
    print("Cấu trúc mới:")
    print()
    print("bottele/")
    print("├── payment/        # Auto payment module")
    print("├── scripts/        # Helper scripts")
    print("├── tests/          # Test suite")
    print("├── docs/           # Documentation")
    print("├── main.py         # Entry point")
    print("└── README.md       # Main README")
    print()
    
    print("Cách sử dụng:")
    print()
    print("  # Chạy bot")
    print("  python main.py")
    print()
    print("  # Thêm thẻ")
    print("  python scripts/add_cards.py add")
    print()
    print("  # Chạy tests")
    print("  python scripts/test_all.py")
    print()
    print("  # Đọc docs")
    print("  docs/01_START_HERE.md")
    print()

def main():
    print()
    print("=" * 60)
    print("TỔ CHỨC LẠI SOURCE CODE")
    print("=" * 60)
    print()
    print("Hiện tại có 28 files ở root, khá lộn xộn.")
    print()
    print("Bạn muốn:")
    print("  1. Tổ chức lại thành 5 thư mục gọn gàng")
    print("  2. Giữ nguyên (không làm gì)")
    print()
    
    response = input("Chọn (1/2): ").strip()
    
    if response == '2':
        print()
        print("OK! Giữ nguyên structure hiện tại.")
        print()
        print("💡 Tips:")
        print("   - Đọc README.md để hiểu source code")
        print("   - Đọc HUONG_DAN_DON_GIAN.md để hiểu 28 files")
        print("   - Chạy: python run_all_tests.py")
        print()
        return
    
    if response != '1':
        print("Lựa chọn không hợp lệ. Đã hủy.")
        return
    
    print()
    print("Bắt đầu tổ chức lại...")
    print()
    
    # Tạo thư mục
    create_directories()
    
    # Di chuyển files
    move_files()
    
    # Tạo __init__.py
    create_init_files()
    
    # Tạo README
    create_readme()
    
    # Tổng kết
    show_summary()
    
    print("=" * 60)
    print("✅ HOÀN TẤT!")
    print("=" * 60)
    print()
    print("📝 Bước tiếp theo:")
    print("   1. Kiểm tra cấu trúc mới")
    print("   2. Chạy tests: python scripts/test_all.py")
    print("   3. Đọc docs: docs/01_START_HERE.md")
    print()

if __name__ == "__main__":
    main()
