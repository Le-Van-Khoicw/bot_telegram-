"""
Script thêm thẻ test vào database
Chạy: python add_test_cards.py
"""

import sys
import os

# Add pay_kiro to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'pay_kiro'))

from database import CardDatabase


def add_test_cards():
    """Thêm thẻ test"""
    
    db = CardDatabase()
    
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
            'notes': 'Thẻ test 1 - Priority cao'
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
            'notes': 'Thẻ test 2 - Priority trung bình'
        },
        {
            'card_number': '4111111111111111',
            'card_holder': 'LE VAN C',
            'expiry_month': '03',
            'expiry_year': '27',
            'cvv': '789',
            'billing_address': '789 Test Road',
            'billing_city': 'Danang',
            'billing_state': 'Danang',
            'billing_zip': '550000',
            'billing_country': 'Vietnam',
            'priority': 3,
            'notes': 'Thẻ test 3 - Priority thấp'
        }
    ]
    
    print("=" * 60)
    print("THÊM THẺ TEST VÀO DATABASE")
    print("=" * 60)
    print()
    
    added_count = 0
    
    for i, card in enumerate(test_cards, 1):
        try:
            card_id = db.add_card(card)
            print(f"✓ [{i}/{len(test_cards)}] Added card ID: {card_id}")
            print(f"   Số thẻ: ****{card['card_number'][-4:]}")
            print(f"   Chủ thẻ: {card['card_holder']}")
            print(f"   Priority: {card['priority']}")
            print()
            added_count += 1
        except Exception as e:
            print(f"✗ [{i}/{len(test_cards)}] Failed to add card: {e}")
            print()
    
    print("=" * 60)
    print(f"✅ HOÀN TẤT! Đã thêm {added_count}/{len(test_cards)} thẻ")
    print("=" * 60)
    print()
    
    # Show stats
    stats = db.get_stats()
    print("📊 THỐNG KÊ:")
    print(f"   Thẻ active: {stats['active_cards']}")
    print(f"   Giao dịch thành công: {stats['success_transactions']}")
    print(f"   Giao dịch thất bại: {stats['failed_transactions']}")
    print()


def list_all_cards():
    """Hiển thị tất cả thẻ"""
    
    db = CardDatabase()
    cards = db.get_active_cards()
    
    if not cards:
        print("Không có thẻ nào trong database!")
        return
    
    print("=" * 60)
    print(f"DANH SÁCH THẺ ({len(cards)} thẻ)")
    print("=" * 60)
    print()
    
    for card in cards:
        print(f"ID: {card['id']}")
        print(f"  Số thẻ: ****{card['card_number'][-4:]}")
        print(f"  Chủ thẻ: {card['card_holder']}")
        print(f"  Hết hạn: {card['expiry_month']}/{card['expiry_year']}")
        print(f"  Trạng thái: {card['status']}")
        print(f"  Thành công: {card['success_count']} | Thất bại: {card['fail_count']}")
        print(f"  Priority: {card['priority']}")
        if card['notes']:
            print(f"  Ghi chú: {card['notes']}")
        print()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Quản lý thẻ thanh toán')
    parser.add_argument(
        'action',
        choices=['add', 'list'],
        help='add: Thêm thẻ test | list: Xem danh sách thẻ'
    )
    
    args = parser.parse_args()
    
    if args.action == 'add':
        add_test_cards()
    elif args.action == 'list':
        list_all_cards()
