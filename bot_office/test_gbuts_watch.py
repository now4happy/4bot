import sys
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))

def is_target_item(item):
    title = item.get("title", {}).get("ko", "").lower()
    keywords = ["claude", "클로드", "supergrok", "슈퍼그록", "슈퍼 그록", "grok", "그록"]
    if not any(k in title for k in keywords): return False
    if item.get("status") != "ON_SALE": return False
    member_count = item.get("memberCount", 0)
    member_limit = item.get("memberLimit", 0)
    if member_limit > 0 and member_count >= member_limit: return False
    end_str = item.get("subscriptionEndsAt")
    if not end_str: return False
    try:
        end_dt = datetime.strptime(end_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=KST)
        remain_days = (end_dt - datetime.now(KST)).days
        if remain_days < 0 or remain_days > 31: return False
    except Exception: return False
    return True

def run_tests():
    test_items = [
        {"title": {"ko": "[Claude] 프로 공유"}, "status": "ON_SALE", "memberCount": 2, "memberLimit": 6, "subscriptionEndsAt": (datetime.now(KST) + timedelta(days=20)).strftime("%Y-%m-%d %H:%M:%S")},
        {"title": {"ko": "슈퍼그록 단독"}, "status": "ON_SALE", "memberCount": 1, "memberLimit": 3, "subscriptionEndsAt": (datetime.now(KST) + timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")},
        {"title": {"ko": "[Claude] 프로 공유"}, "status": "ON_SALE", "memberCount": 6, "memberLimit": 6, "subscriptionEndsAt": (datetime.now(KST) + timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")},
        {"title": {"ko": "Claude 연장"}, "status": "ON_SALE", "memberCount": 0, "memberLimit": 7, "subscriptionEndsAt": (datetime.now(KST) + timedelta(days=40)).strftime("%Y-%m-%d %H:%M:%S")},
    ]
    expected = [True, True, False, False]
    for i, (item, exp) in enumerate(zip(test_items, expected)):
        result = is_target_item(item)
        status = "✅ PASS" if result == exp else "❌ FAIL"
        print(f"필터 테스트 {i+1}: {status} (기대={exp}, 실제={result})")

    print("\n[변동 감지 시뮬레이션]")
    old_state = {"price": 10000, "member_count": 2}
    new_state = {"price": 8000, "member_count": 2}
    changes = []
    if old_state["price"] != new_state["price"]: changes.append("가격 변동")
    if old_state["member_count"] != new_state["member_count"]: changes.append("인원 변동")
    if changes:
        print(f"✅ PASS: 변경 사항 감지됨 -> {', '.join(changes)}")
    else:
        print("❌ FAIL: 변경 사항을 감지하지 못함")

if __name__ == "__main__":
    run_tests()
