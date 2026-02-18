"""End-to-end test for auth + memory system."""
import requests
import json
import time

BASE = "http://127.0.0.1:8000"

# 1. Register fresh user
print("=== REGISTER ===")
r = requests.post(f"{BASE}/api/auth/register", json={
    "username": "recall_demo",
    "password": "test123456",
    "display_name": "Recall Demo"
})
if r.status_code == 400:
    print("User exists, logging in...")
    r = requests.post(f"{BASE}/api/auth/login", json={
        "username": "recall_demo",
        "password": "test123456"
    })
data = r.json()
print(f"Status: {r.status_code}")
print(f"User: {data['user']['display_name']} (guest={data['user'].get('is_guest')})")
token = data["token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# 2. Verify /me
print("\n=== ME ===")
me = requests.get(f"{BASE}/api/auth/me", headers=headers).json()
print(f"ID: {me['id']}, Name: {me['display_name']}, Provider: {me['auth_provider']}")

# 3. Chat with personal info
print("\n=== CHAT 1: Introduce ===")
r2 = requests.post(f"{BASE}/api/chat", json={
    "session_id": "recall_sess",
    "message": "สวัสดีครับ ผมชื่อโดม อายุ 28 ปี เป็นโปรแกรมเมอร์"
}, headers=headers)
d2 = r2.json()
print(f"Reply: {d2['response'][:120]}")
print(f"Learned facts: {d2.get('learned_facts', [])}")

# 4. Check stored facts
print("\n=== STORED FACTS ===")
r3 = requests.get(f"{BASE}/api/user/facts", headers=headers)
facts = r3.json()
print(f"Total facts: {len(facts)}")
for f in facts:
    cat = f["category"]
    key = f["key"]
    val = f["value"]
    conf = f["confidence"]
    print(f"  [{cat}] {key}: {val} (confidence={conf})")

# 5. Profile context
print("\n=== PROFILE CONTEXT ===")
r4 = requests.get(f"{BASE}/api/user/profile-context", headers=headers)
print(r4.json()["context"][:300])

# 6. Ask the bot to recall
print("\n=== CHAT 2: Recall Test ===")
time.sleep(1)
r5 = requests.post(f"{BASE}/api/chat", json={
    "session_id": "recall_sess",
    "message": "คุณจำได้ไหมว่าผมชื่ออะไร ทำอาชีพอะไร?"
}, headers=headers)
d5 = r5.json()
print(f"Reply: {d5['response'][:200]}")
print(f"Memory used: {d5.get('memory_used')}")

# 7. Guest mode test
print("\n=== GUEST MODE ===")
rg = requests.post(f"{BASE}/api/auth/guest")
gdata = rg.json()
print(f"Guest: {gdata['user']['display_name']} (is_guest={gdata['user']['is_guest']})")
gh = {"Authorization": f"Bearer {gdata['token']}", "Content-Type": "application/json"}
rg2 = requests.post(f"{BASE}/api/chat", json={
    "session_id": "guest_sess",
    "message": "ผมชื่อทดสอบ"
}, headers=gh)
gd = rg2.json()
print(f"Guest reply: {gd['response'][:100]}")
print(f"Guest learned_facts: {gd.get('learned_facts', [])}")

# 8. Conversations list
print("\n=== CONVERSATIONS ===")
r6 = requests.get(f"{BASE}/api/user/conversations", headers=headers)
convs = r6.json()
print(f"Total conversations: {len(convs)}")
for c in convs:
    print(f"  [{c['id'][:8]}] {c['title']}")

print("\n=== ALL TESTS PASSED ===")
