#!/usr/bin/env python3
"""
Comprehensive backend regression test for Fmail API.
Tests all route groups with success and failure cases.
Uses demo@fmail.com / demo123 for authenticated endpoints.
"""
import httpx
import json
import time
import base64
import sys

BASE_URL = "https://fmail-staging.preview.emergentagent.com/api"
DEMO_EMAIL = "demo@fmail.com"
DEMO_PASSWORD = "demo123"

# Test results tracking
passed = 0
failed = 0
failures = []

def test(name, condition, details=""):
    global passed, failed, failures
    if condition:
        passed += 1
        print(f"✓ {name}")
    else:
        failed += 1
        failures.append(f"{name}: {details}")
        print(f"✗ {name}: {details}")

def get_demo_token():
    """Login with demo account and return token."""
    try:
        r = httpx.post(f"{BASE_URL}/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD}, timeout=30)
        if r.status_code == 200:
            return r.json()["token"]
        return None
    except Exception as e:
        print(f"Failed to get demo token: {e}")
        return None

def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}

print("=" * 80)
print("FMAIL BACKEND COMPREHENSIVE REGRESSION TEST")
print("=" * 80)
print()

# ============================================================================
# 1. ROOT / HEALTH CHECK
# ============================================================================
print("1. ROOT / HEALTH CHECK")
print("-" * 80)
try:
    r = httpx.get(f"{BASE_URL}/", timeout=30)
    test("GET / returns 200", r.status_code == 200, f"Got {r.status_code}")
    test("GET / returns status ok", r.json().get("status") == "ok", f"Got {r.json()}")
except Exception as e:
    test("GET / returns 200", False, str(e))
    test("GET / returns status ok", False, str(e))
print()

# ============================================================================
# 2. SIGNUP VALIDATION AND OTP FAIL-CLOSED
# ============================================================================
print("2. SIGNUP VALIDATION AND OTP FAIL-CLOSED")
print("-" * 80)

# Test OTP request without Resend configured
try:
    r = httpx.post(f"{BASE_URL}/auth/request-otp", json={"email": "newuser@test.com", "purpose": "signup"}, timeout=30)
    test("POST /auth/request-otp returns 503 (no Resend)", r.status_code == 503, f"Got {r.status_code}")
    response_text = r.text.lower()
    test("OTP response has safe error message", "unavailable" in response_text or "temporarily" in response_text, f"Got: {r.text[:200]}")
    # CRITICAL: Check no devCode or test OTP exposed
    test("NO devCode exposed in OTP response", "devcode" not in response_text and "dev_code" not in response_text, f"Response: {r.text[:200]}")
    test("NO test OTP exposed in OTP response", "123456" not in response_text and "000000" not in response_text, f"Response: {r.text[:200]}")
except Exception as e:
    test("POST /auth/request-otp returns 503 (no Resend)", False, str(e))
    test("OTP response has safe error message", False, str(e))
    test("NO devCode exposed in OTP response", False, str(e))
    test("NO test OTP exposed in OTP response", False, str(e))

# Test signup requires OTP code
try:
    r = httpx.post(f"{BASE_URL}/auth/signup", json={
        "email": "newuser@test.com",
        "password": "password123",
        "name": "New User",
        "username": "newuser",
        "code": "000000"
    }, timeout=30)
    test("POST /auth/signup with invalid code returns 400", r.status_code == 400, f"Got {r.status_code}")
    test("Signup error mentions verification", "verif" in r.text.lower() or "code" in r.text.lower(), f"Got: {r.text[:200]}")
except Exception as e:
    test("POST /auth/signup with invalid code returns 400", False, str(e))
    test("Signup error mentions verification", False, str(e))

print()

# ============================================================================
# 3. VERIFY/RESET INVALID/EXPIRED/WRONG CODE AND COOLDOWN/RATE-LIMIT
# ============================================================================
print("3. VERIFY/RESET INVALID/EXPIRED/WRONG CODE AND COOLDOWN/RATE-LIMIT")
print("-" * 80)

# Test verify-otp with no OTP requested
try:
    r = httpx.post(f"{BASE_URL}/auth/verify-otp", json={"email": "test@test.com", "code": "123456", "purpose": "signup"}, timeout=30)
    test("POST /auth/verify-otp without request returns 400", r.status_code == 400, f"Got {r.status_code}")
    test("Verify error mentions request code first", "request" in r.text.lower(), f"Got: {r.text[:200]}")
except Exception as e:
    test("POST /auth/verify-otp without request returns 400", False, str(e))
    test("Verify error mentions request code first", False, str(e))

# Test reset-password with invalid code
try:
    r = httpx.post(f"{BASE_URL}/auth/reset-password", json={"email": DEMO_EMAIL, "code": "999999", "password": "newpass123"}, timeout=30)
    test("POST /auth/reset-password with invalid code returns 400", r.status_code == 400, f"Got {r.status_code}")
except Exception as e:
    test("POST /auth/reset-password with invalid code returns 400", False, str(e))

# Test OTP cooldown - request twice quickly
try:
    r1 = httpx.post(f"{BASE_URL}/auth/request-otp", json={"email": "cooldown@test.com", "purpose": "signup"}, timeout=30)
    time.sleep(1)  # Wait 1 second (cooldown is 30s)
    r2 = httpx.post(f"{BASE_URL}/auth/request-otp", json={"email": "cooldown@test.com", "purpose": "signup"}, timeout=30)
    # Both should return 503 (no Resend) or second should return 429 (cooldown)
    test("OTP cooldown enforced or service unavailable", r2.status_code in [429, 503], f"Got {r2.status_code}")
except Exception as e:
    test("OTP cooldown enforced or service unavailable", False, str(e))

print()

# ============================================================================
# 4. LOGIN/ME/LOGOUT-EQUIVALENT SESSION BEHAVIOR
# ============================================================================
print("4. LOGIN/ME/LOGOUT-EQUIVALENT SESSION BEHAVIOR")
print("-" * 80)

# Test login with demo account
token = None
try:
    r = httpx.post(f"{BASE_URL}/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD}, timeout=30)
    test("POST /auth/login with demo account returns 200", r.status_code == 200, f"Got {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        test("Login returns token", "token" in data, f"Keys: {list(data.keys())}")
        test("Login returns user", "user" in data, f"Keys: {list(data.keys())}")
        token = data.get("token")
    else:
        test("Login returns token", False, f"Status {r.status_code}")
        test("Login returns user", False, f"Status {r.status_code}")
except Exception as e:
    test("POST /auth/login with demo account returns 200", False, str(e))
    test("Login returns token", False, str(e))
    test("Login returns user", False, str(e))

# Test login with wrong password
try:
    r = httpx.post(f"{BASE_URL}/auth/login", json={"email": DEMO_EMAIL, "password": "wrongpassword"}, timeout=30)
    test("POST /auth/login with wrong password returns 401", r.status_code == 401, f"Got {r.status_code}")
except Exception as e:
    test("POST /auth/login with wrong password returns 401", False, str(e))

# Test /auth/me with valid token
if token:
    try:
        r = httpx.get(f"{BASE_URL}/auth/me", headers=auth_headers(token), timeout=30)
        test("GET /auth/me with valid token returns 200", r.status_code == 200, f"Got {r.status_code}")
        if r.status_code == 200:
            user = r.json()
            test("GET /auth/me returns user email", user.get("email") == DEMO_EMAIL, f"Got: {user.get('email')}")
            test("GET /auth/me does not expose password", "password" not in user, f"Keys: {list(user.keys())}")
    except Exception as e:
        test("GET /auth/me with valid token returns 200", False, str(e))
        test("GET /auth/me returns user email", False, str(e))
        test("GET /auth/me does not expose password", False, str(e))
else:
    test("GET /auth/me with valid token returns 200", False, "No token available")
    test("GET /auth/me returns user email", False, "No token available")
    test("GET /auth/me does not expose password", False, "No token available")

# Test /auth/me with invalid token
try:
    r = httpx.get(f"{BASE_URL}/auth/me", headers={"Authorization": "Bearer invalid_token_12345"}, timeout=30)
    test("GET /auth/me with invalid token returns 401", r.status_code == 401, f"Got {r.status_code}")
except Exception as e:
    test("GET /auth/me with invalid token returns 401", False, str(e))

# Test /auth/me without token
try:
    r = httpx.get(f"{BASE_URL}/auth/me", timeout=30)
    test("GET /auth/me without token returns 401 or 403", r.status_code in [401, 403], f"Got {r.status_code}")
except Exception as e:
    test("GET /auth/me without token returns 401 or 403", False, str(e))

print()

# Get fresh token for remaining tests
if not token:
    token = get_demo_token()
    if not token:
        print("CRITICAL: Cannot get demo token. Remaining tests will fail.")
        print()

# ============================================================================
# 5. HANDLE AVAILABILITY
# ============================================================================
print("5. HANDLE AVAILABILITY")
print("-" * 80)

try:
    r = httpx.get(f"{BASE_URL}/auth/check-handle?handle=demo", timeout=30)
    test("GET /auth/check-handle for 'demo' returns 200", r.status_code == 200, f"Got {r.status_code}")
    test("Handle 'demo' is taken", r.json().get("available") == False, f"Got: {r.json()}")
except Exception as e:
    test("GET /auth/check-handle for 'demo' returns 200", False, str(e))
    test("Handle 'demo' is taken", False, str(e))

try:
    r = httpx.get(f"{BASE_URL}/auth/check-handle?handle=Demo", timeout=30)
    test("Handle check is case-insensitive", r.json().get("available") == False, f"Got: {r.json()}")
except Exception as e:
    test("Handle check is case-insensitive", False, str(e))

try:
    unique_handle = f"testuser{int(time.time())}"
    r = httpx.get(f"{BASE_URL}/auth/check-handle?handle={unique_handle}", timeout=30)
    test("Unique handle is available", r.json().get("available") == True, f"Got: {r.json()}")
except Exception as e:
    test("Unique handle is available", False, str(e))

try:
    r = httpx.get(f"{BASE_URL}/auth/check-handle?handle=ab", timeout=30)
    test("Handle 'ab' fails min length validation", r.json().get("available") == False, f"Got: {r.json()}")
    test("Min length error mentions 3 characters", "3" in r.json().get("reason", ""), f"Got: {r.json()}")
except Exception as e:
    test("Handle 'ab' fails min length validation", False, str(e))
    test("Min length error mentions 3 characters", False, str(e))

try:
    r = httpx.get(f"{BASE_URL}/auth/check-handle?handle=bad handle!", timeout=30)
    test("Handle with invalid chars fails validation", r.json().get("available") == False, f"Got: {r.json()}")
except Exception as e:
    test("Handle with invalid chars fails validation", False, str(e))

print()

# ============================================================================
# 6. PROFILE UPDATE
# ============================================================================
print("6. PROFILE UPDATE")
print("-" * 80)

if token:
    try:
        r = httpx.put(f"{BASE_URL}/auth/profile", headers=auth_headers(token), json={"name": "Demo User Updated"}, timeout=30)
        test("PUT /auth/profile returns 200", r.status_code == 200, f"Got {r.status_code}")
        test("Profile update reflects new name", r.json().get("name") == "Demo User Updated", f"Got: {r.json().get('name')}")
    except Exception as e:
        test("PUT /auth/profile returns 200", False, str(e))
        test("Profile update reflects new name", False, str(e))
else:
    test("PUT /auth/profile returns 200", False, "No token")
    test("Profile update reflects new name", False, "No token")

print()

# ============================================================================
# 7. PERMISSIONS
# ============================================================================
print("7. PERMISSIONS")
print("-" * 80)

if token:
    try:
        perms = {"notifications": True, "camera": True, "microphone": False}
        r = httpx.put(f"{BASE_URL}/auth/permissions", headers=auth_headers(token), json={"permissions": perms}, timeout=30)
        test("PUT /auth/permissions returns 200", r.status_code == 200, f"Got {r.status_code}")
        test("Permissions update reflects changes", r.json().get("permissions", {}).get("camera") == True, f"Got: {r.json().get('permissions')}")
    except Exception as e:
        test("PUT /auth/permissions returns 200", False, str(e))
        test("Permissions update reflects changes", False, str(e))
else:
    test("PUT /auth/permissions returns 200", False, "No token")
    test("Permissions update reflects changes", False, "No token")

print()

# ============================================================================
# 8. DELETE ACCOUNT SAFETY (skip actual deletion for demo account)
# ============================================================================
print("8. DELETE ACCOUNT SAFETY")
print("-" * 80)

# We won't actually delete the demo account, but test that endpoint requires auth
try:
    r = httpx.delete(f"{BASE_URL}/auth/account", timeout=30)
    test("DELETE /auth/account without token returns 401/403", r.status_code in [401, 403], f"Got {r.status_code}")
except Exception as e:
    test("DELETE /auth/account without token returns 401/403", False, str(e))

print()

# ============================================================================
# 9. INBOX FOLDERS/FILTERS/SEARCH
# ============================================================================
print("9. INBOX FOLDERS/FILTERS/SEARCH")
print("-" * 80)

if token:
    try:
        r = httpx.get(f"{BASE_URL}/emails?folder=inbox", headers=auth_headers(token), timeout=30)
        test("GET /emails?folder=inbox returns 200", r.status_code == 200, f"Got {r.status_code}")
        test("Inbox returns array", isinstance(r.json(), list), f"Got type: {type(r.json())}")
    except Exception as e:
        test("GET /emails?folder=inbox returns 200", False, str(e))
        test("Inbox returns array", False, str(e))

    try:
        r = httpx.get(f"{BASE_URL}/emails?folder=sent", headers=auth_headers(token), timeout=30)
        test("GET /emails?folder=sent returns 200", r.status_code == 200, f"Got {r.status_code}")
    except Exception as e:
        test("GET /emails?folder=sent returns 200", False, str(e))

    try:
        r = httpx.get(f"{BASE_URL}/emails?folder=drafts", headers=auth_headers(token), timeout=30)
        test("GET /emails?folder=drafts returns 200", r.status_code == 200, f"Got {r.status_code}")
    except Exception as e:
        test("GET /emails?folder=drafts returns 200", False, str(e))

    try:
        r = httpx.get(f"{BASE_URL}/emails?folder=trash", headers=auth_headers(token), timeout=30)
        test("GET /emails?folder=trash returns 200", r.status_code == 200, f"Got {r.status_code}")
    except Exception as e:
        test("GET /emails?folder=trash returns 200", False, str(e))

    try:
        r = httpx.get(f"{BASE_URL}/emails?folder=important", headers=auth_headers(token), timeout=30)
        test("GET /emails?folder=important returns 200", r.status_code == 200, f"Got {r.status_code}")
    except Exception as e:
        test("GET /emails?folder=important returns 200", False, str(e))

    try:
        r = httpx.get(f"{BASE_URL}/emails?filter=unread", headers=auth_headers(token), timeout=30)
        test("GET /emails?filter=unread returns 200", r.status_code == 200, f"Got {r.status_code}")
    except Exception as e:
        test("GET /emails?filter=unread returns 200", False, str(e))
else:
    for _ in range(6):
        test("Email folder/filter endpoint", False, "No token")

print()

# ============================================================================
# 10. THREAD READ
# ============================================================================
print("10. THREAD READ")
print("-" * 80)

thread_id = None
if token:
    try:
        r = httpx.get(f"{BASE_URL}/emails?folder=inbox", headers=auth_headers(token), timeout=30)
        if r.status_code == 200 and len(r.json()) > 0:
            thread_id = r.json()[0].get("threadId")
            if thread_id:
                r2 = httpx.get(f"{BASE_URL}/threads/{thread_id}", headers=auth_headers(token), timeout=30)
                test("GET /threads/{tid} returns 200", r2.status_code == 200, f"Got {r2.status_code}")
                test("Thread response has messages", "messages" in r2.json(), f"Keys: {list(r2.json().keys())}")
            else:
                test("GET /threads/{tid} returns 200", False, "No threadId in inbox")
                test("Thread response has messages", False, "No threadId in inbox")
        else:
            test("GET /threads/{tid} returns 200", False, "Empty inbox")
            test("Thread response has messages", False, "Empty inbox")
    except Exception as e:
        test("GET /threads/{tid} returns 200", False, str(e))
        test("Thread response has messages", False, str(e))
else:
    test("GET /threads/{tid} returns 200", False, "No token")
    test("Thread response has messages", False, "No token")

# Test thread not found
if token:
    try:
        r = httpx.get(f"{BASE_URL}/threads/nonexistent-thread-id", headers=auth_headers(token), timeout=30)
        test("GET /threads/{invalid} returns 404", r.status_code == 404, f"Got {r.status_code}")
    except Exception as e:
        test("GET /threads/{invalid} returns 404", False, str(e))
else:
    test("GET /threads/{invalid} returns 404", False, "No token")

print()

# ============================================================================
# 11. COMPOSE SEND/DRAFT/REPLY/FORWARD/DELETE/TRASH WITH CC/BCC/ATTACHMENTS
# ============================================================================
print("11. COMPOSE SEND/DRAFT/REPLY/FORWARD/DELETE/TRASH WITH CC/BCC/ATTACHMENTS")
print("-" * 80)

compose_id = None
if token:
    # Test compose with cc/bcc/attachments
    try:
        r = httpx.post(f"{BASE_URL}/emails/compose", headers=auth_headers(token), json={
            "to": "test@example.com",
            "subject": "Test Email with Cc/Bcc",
            "body": "This is a test email.",
            "cc": "cc@example.com",
            "bcc": "bcc@example.com",
            "attachments": [{"name": "test.pdf", "type": "pdf", "size": "100KB", "data": "base64data"}],
            "draft": False
        }, timeout=30)
        test("POST /emails/compose with cc/bcc/attachments returns 200", r.status_code == 200, f"Got {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            test("Compose stores cc field", data.get("cc") == "cc@example.com", f"Got: {data.get('cc')}")
            test("Compose stores bcc field", data.get("bcc") == "bcc@example.com", f"Got: {data.get('bcc')}")
            test("Compose stores attachments", len(data.get("attachments", [])) == 1, f"Got: {data.get('attachments')}")
            test("Compose sets folder to sent", data.get("folder") == "sent", f"Got: {data.get('folder')}")
            compose_id = data.get("threadId")
    except Exception as e:
        test("POST /emails/compose with cc/bcc/attachments returns 200", False, str(e))
        test("Compose stores cc field", False, str(e))
        test("Compose stores bcc field", False, str(e))
        test("Compose stores attachments", False, str(e))
        test("Compose sets folder to sent", False, str(e))

    # Test draft compose
    draft_id = None
    try:
        r = httpx.post(f"{BASE_URL}/emails/compose", headers=auth_headers(token), json={
            "to": "draft@example.com",
            "subject": "Draft Email",
            "body": "This is a draft.",
            "draft": True
        }, timeout=30)
        test("POST /emails/compose with draft=true returns 200", r.status_code == 200, f"Got {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            test("Draft sets folder to drafts", data.get("folder") == "drafts", f"Got: {data.get('folder')}")
            draft_id = data.get("threadId")
    except Exception as e:
        test("POST /emails/compose with draft=true returns 200", False, str(e))
        test("Draft sets folder to drafts", False, str(e))

    # Test draft appears in drafts folder
    if draft_id:
        try:
            r = httpx.get(f"{BASE_URL}/emails?folder=drafts", headers=auth_headers(token), timeout=30)
            drafts = r.json()
            test("Draft appears in GET /emails?folder=drafts", any(d.get("threadId") == draft_id for d in drafts), f"Draft ID {draft_id} not in drafts")
        except Exception as e:
            test("Draft appears in GET /emails?folder=drafts", False, str(e))

    # Test delete email (move to trash)
    if compose_id:
        try:
            r = httpx.delete(f"{BASE_URL}/emails/{compose_id}", headers=auth_headers(token), timeout=30)
            test("DELETE /emails/{tid} first time returns 200", r.status_code == 200, f"Got {r.status_code}")
            test("DELETE returns ok=true", r.json().get("ok") == True, f"Got: {r.json()}")
        except Exception as e:
            test("DELETE /emails/{tid} first time returns 200", False, str(e))
            test("DELETE returns ok=true", False, str(e))

        # Verify moved to trash
        try:
            r = httpx.get(f"{BASE_URL}/emails?folder=trash", headers=auth_headers(token), timeout=30)
            trash = r.json()
            test("Deleted email appears in trash", any(e.get("threadId") == compose_id for e in trash), f"Thread {compose_id} not in trash")
        except Exception as e:
            test("Deleted email appears in trash", False, str(e))

        # Test permanent delete (second delete)
        try:
            r = httpx.delete(f"{BASE_URL}/emails/{compose_id}", headers=auth_headers(token), timeout=30)
            test("DELETE /emails/{tid} second time returns 200", r.status_code == 200, f"Got {r.status_code}")
        except Exception as e:
            test("DELETE /emails/{tid} second time returns 200", False, str(e))

        # Verify permanently deleted
        try:
            r = httpx.get(f"{BASE_URL}/emails?folder=trash", headers=auth_headers(token), timeout=30)
            trash = r.json()
            test("Permanently deleted email not in trash", not any(e.get("threadId") == compose_id for e in trash), f"Thread {compose_id} still in trash")
        except Exception as e:
            test("Permanently deleted email not in trash", False, str(e))

    # Test PATCH email (star, important, read, folder)
    if thread_id:
        try:
            r = httpx.patch(f"{BASE_URL}/emails/{thread_id}", headers=auth_headers(token), json={"star": True, "important": True}, timeout=30)
            test("PATCH /emails/{tid} returns 200", r.status_code == 200, f"Got {r.status_code}")
            test("PATCH returns updated fields", r.json().get("star") == True and r.json().get("important") == True, f"Got: {r.json()}")
        except Exception as e:
            test("PATCH /emails/{tid} returns 200", False, str(e))
            test("PATCH returns updated fields", False, str(e))
else:
    for _ in range(15):
        test("Compose/draft/delete endpoint", False, "No token")

print()

# ============================================================================
# 12. AI COMPOSE/REPLY/UNDERSTAND/ASK/HISTORY/EMAIL-TO-TASK/FILE-SUMMARY
# ============================================================================
print("12. AI COMPOSE/REPLY/UNDERSTAND/ASK/HISTORY/EMAIL-TO-TASK/FILE-SUMMARY")
print("-" * 80)

if token:
    # Test AI compose
    try:
        r = httpx.post(f"{BASE_URL}/ai/compose", headers=auth_headers(token), json={
            "instruction": "Write a thank you email to the team",
            "tone": "Professional"
        }, timeout=60)
        test("POST /ai/compose returns 200", r.status_code == 200, f"Got {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            test("AI compose returns subject", "subject" in data, f"Keys: {list(data.keys())}")
            test("AI compose returns body", "body" in data, f"Keys: {list(data.keys())}")
    except Exception as e:
        test("POST /ai/compose returns 200", False, str(e))
        test("AI compose returns subject", False, str(e))
        test("AI compose returns body", False, str(e))

    # Test AI reply
    if thread_id:
        try:
            r = httpx.post(f"{BASE_URL}/ai/reply", headers=auth_headers(token), json={
                "threadId": thread_id,
                "tone": "Friendly",
                "action": "reply"
            }, timeout=60)
            test("POST /ai/reply returns 200", r.status_code == 200, f"Got {r.status_code}")
            test("AI reply returns text", "text" in r.json(), f"Keys: {list(r.json().keys())}")
        except Exception as e:
            test("POST /ai/reply returns 200", False, str(e))
            test("AI reply returns text", False, str(e))

    # Test AI understand
    if thread_id:
        try:
            r = httpx.post(f"{BASE_URL}/ai/understand/{thread_id}", headers=auth_headers(token), timeout=60)
            test("POST /ai/understand/{tid} returns 200", r.status_code == 200, f"Got {r.status_code}")
            if r.status_code == 200:
                data = r.json()
                test("AI understand returns intent", "intent" in data, f"Keys: {list(data.keys())}")
        except Exception as e:
            test("POST /ai/understand/{tid} returns 200", False, str(e))
            test("AI understand returns intent", False, str(e))

    # Test AI thread
    if thread_id:
        try:
            r = httpx.post(f"{BASE_URL}/ai/thread/{thread_id}", headers=auth_headers(token), timeout=60)
            test("POST /ai/thread/{tid} returns 200", r.status_code == 200, f"Got {r.status_code}")
            if r.status_code == 200:
                data = r.json()
                test("AI thread returns summary", "summary" in data, f"Keys: {list(data.keys())}")
        except Exception as e:
            test("POST /ai/thread/{tid} returns 200", False, str(e))
            test("AI thread returns summary", False, str(e))

    # Test AI ask
    try:
        r = httpx.post(f"{BASE_URL}/ai/ask", headers=auth_headers(token), json={"question": "What are my urgent tasks?"}, timeout=60)
        test("POST /ai/ask returns 200", r.status_code == 200, f"Got {r.status_code}")
        test("AI ask returns answer", "answer" in r.json(), f"Keys: {list(r.json().keys())}")
    except Exception as e:
        test("POST /ai/ask returns 200", False, str(e))
        test("AI ask returns answer", False, str(e))

    # Test AI chat history
    try:
        r = httpx.get(f"{BASE_URL}/ai/chat-history", headers=auth_headers(token), timeout=30)
        test("GET /ai/chat-history returns 200", r.status_code == 200, f"Got {r.status_code}")
        test("Chat history returns array", isinstance(r.json(), list), f"Got type: {type(r.json())}")
    except Exception as e:
        test("GET /ai/chat-history returns 200", False, str(e))
        test("Chat history returns array", False, str(e))

    # Test AI email-to-task
    if thread_id:
        try:
            r = httpx.post(f"{BASE_URL}/ai/email-to-task/{thread_id}", headers=auth_headers(token), timeout=60)
            test("POST /ai/email-to-task/{tid} returns 200", r.status_code == 200, f"Got {r.status_code}")
            if r.status_code == 200:
                data = r.json()
                test("Email-to-task returns task with title", "title" in data, f"Keys: {list(data.keys())}")
        except Exception as e:
            test("POST /ai/email-to-task/{tid} returns 200", False, str(e))
            test("Email-to-task returns task with title", False, str(e))

    # Test AI file-summary (need to create a file first)
    file_id = None
    try:
        r = httpx.post(f"{BASE_URL}/files", headers=auth_headers(token), data={
            "name": "test_document.pdf",
            "type": "pdf",
            "size": "100KB",
            "data": base64.b64encode(b"test file content").decode()
        }, timeout=30)
        if r.status_code == 200:
            file_id = r.json().get("id")
    except Exception as e:
        pass

    if file_id:
        try:
            r = httpx.post(f"{BASE_URL}/ai/file-summary/{file_id}", headers=auth_headers(token), timeout=60)
            test("POST /ai/file-summary/{fid} returns 200", r.status_code == 200, f"Got {r.status_code}")
            test("File summary returns summary", "summary" in r.json(), f"Keys: {list(r.json().keys())}")
        except Exception as e:
            test("POST /ai/file-summary/{fid} returns 200", False, str(e))
            test("File summary returns summary", False, str(e))
    else:
        test("POST /ai/file-summary/{fid} returns 200", False, "Could not create test file")
        test("File summary returns summary", False, "Could not create test file")
else:
    for _ in range(18):
        test("AI endpoint", False, "No token")

print()

# ============================================================================
# 13. DASHBOARD
# ============================================================================
print("13. DASHBOARD")
print("-" * 80)

if token:
    try:
        r = httpx.get(f"{BASE_URL}/dashboard", headers=auth_headers(token), timeout=30)
        test("GET /dashboard returns 200", r.status_code == 200, f"Got {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            test("Dashboard returns brief", "brief" in data, f"Keys: {list(data.keys())}")
            test("Dashboard returns counts", "counts" in data, f"Keys: {list(data.keys())}")
            test("Dashboard returns tasks", "tasks" in data, f"Keys: {list(data.keys())}")
    except Exception as e:
        test("GET /dashboard returns 200", False, str(e))
        test("Dashboard returns brief", False, str(e))
        test("Dashboard returns counts", False, str(e))
        test("Dashboard returns tasks", False, str(e))
else:
    test("GET /dashboard returns 200", False, "No token")
    test("Dashboard returns brief", False, "No token")
    test("Dashboard returns counts", False, "No token")
    test("Dashboard returns tasks", False, "No token")

print()

# ============================================================================
# 14. TASKS/EVENTS/CONTACTS/FILES CRUD
# ============================================================================
print("14. TASKS/EVENTS/CONTACTS/FILES CRUD")
print("-" * 80)

task_id = None
if token:
    # Tasks
    try:
        r = httpx.get(f"{BASE_URL}/tasks", headers=auth_headers(token), timeout=30)
        test("GET /tasks returns 200", r.status_code == 200, f"Got {r.status_code}")
        test("GET /tasks returns array", isinstance(r.json(), list), f"Got type: {type(r.json())}")
    except Exception as e:
        test("GET /tasks returns 200", False, str(e))
        test("GET /tasks returns array", False, str(e))

    try:
        r = httpx.post(f"{BASE_URL}/tasks", headers=auth_headers(token), json={
            "title": "Test Task",
            "priority": "high",
            "labels": ["Test"]
        }, timeout=30)
        test("POST /tasks returns 200", r.status_code == 200, f"Got {r.status_code}")
        if r.status_code == 200:
            task_id = r.json().get("id")
            test("POST /tasks returns task with id", task_id is not None, f"Got: {r.json()}")
    except Exception as e:
        test("POST /tasks returns 200", False, str(e))
        test("POST /tasks returns task with id", False, str(e))

    if task_id:
        try:
            r = httpx.delete(f"{BASE_URL}/tasks/{task_id}", headers=auth_headers(token), timeout=30)
            test("DELETE /tasks/{tid} returns 200", r.status_code == 200, f"Got {r.status_code}")
        except Exception as e:
            test("DELETE /tasks/{tid} returns 200", False, str(e))

    # Events
    try:
        r = httpx.get(f"{BASE_URL}/events", headers=auth_headers(token), timeout=30)
        test("GET /events returns 200", r.status_code == 200, f"Got {r.status_code}")
    except Exception as e:
        test("GET /events returns 200", False, str(e))

    try:
        r = httpx.post(f"{BASE_URL}/events", headers=auth_headers(token), json={
            "title": "Test Event",
            "start": "2026-12-01T10:00:00Z"
        }, timeout=30)
        test("POST /events returns 200", r.status_code == 200, f"Got {r.status_code}")
        if r.status_code == 200:
            event_id = r.json().get("id")
            if event_id:
                r2 = httpx.delete(f"{BASE_URL}/events/{event_id}", headers=auth_headers(token), timeout=30)
                test("DELETE /events/{eid} returns 200", r2.status_code == 200, f"Got {r2.status_code}")
    except Exception as e:
        test("POST /events returns 200", False, str(e))

    # Contacts
    try:
        r = httpx.get(f"{BASE_URL}/contacts", headers=auth_headers(token), timeout=30)
        test("GET /contacts returns 200", r.status_code == 200, f"Got {r.status_code}")
    except Exception as e:
        test("GET /contacts returns 200", False, str(e))

    try:
        r = httpx.post(f"{BASE_URL}/contacts", headers=auth_headers(token), json={
            "name": "Test Contact",
            "email": "testcontact@example.com"
        }, timeout=30)
        test("POST /contacts returns 200", r.status_code == 200, f"Got {r.status_code}")
    except Exception as e:
        test("POST /contacts returns 200", False, str(e))

    # Files
    try:
        r = httpx.get(f"{BASE_URL}/files", headers=auth_headers(token), timeout=30)
        test("GET /files returns 200", r.status_code == 200, f"Got {r.status_code}")
    except Exception as e:
        test("GET /files returns 200", False, str(e))

    # Test file upload validation (size limit)
    try:
        large_data = base64.b64encode(b"x" * (13 * 1024 * 1024)).decode()  # 13MB
        r = httpx.post(f"{BASE_URL}/files", headers=auth_headers(token), data={
            "name": "large_file.pdf",
            "type": "pdf",
            "size": "13MB",
            "data": large_data
        }, timeout=30)
        test("POST /files with >8MB returns 413", r.status_code == 413, f"Got {r.status_code}")
    except Exception as e:
        test("POST /files with >8MB returns 413", False, str(e))

    # Test file download isolation
    try:
        r = httpx.get(f"{BASE_URL}/files/nonexistent-file-id/download", headers=auth_headers(token), timeout=30)
        test("GET /files/{invalid}/download returns 404", r.status_code == 404, f"Got {r.status_code}")
    except Exception as e:
        test("GET /files/{invalid}/download returns 404", False, str(e))
else:
    for _ in range(13):
        test("CRUD endpoint", False, "No token")

print()

# ============================================================================
# 15. MEMORY/SPACES/DECISIONS/COMMITMENTS/FOLLOWUPS/AUDIT/NOTIFICATIONS
# ============================================================================
print("15. MEMORY/SPACES/DECISIONS/COMMITMENTS/FOLLOWUPS/AUDIT/NOTIFICATIONS")
print("-" * 80)

if token:
    try:
        r = httpx.get(f"{BASE_URL}/memory", headers=auth_headers(token), timeout=30)
        test("GET /memory returns 200", r.status_code == 200, f"Got {r.status_code}")
    except Exception as e:
        test("GET /memory returns 200", False, str(e))

    try:
        r = httpx.post(f"{BASE_URL}/memory", headers=auth_headers(token), json={
            "kind": "Person",
            "title": "Test Person",
            "detail": "Test detail"
        }, timeout=30)
        test("POST /memory returns 200", r.status_code == 200, f"Got {r.status_code}")
    except Exception as e:
        test("POST /memory returns 200", False, str(e))

    try:
        r = httpx.get(f"{BASE_URL}/spaces", headers=auth_headers(token), timeout=30)
        test("GET /spaces returns 200", r.status_code == 200, f"Got {r.status_code}")
    except Exception as e:
        test("GET /spaces returns 200", False, str(e))

    try:
        r = httpx.get(f"{BASE_URL}/decisions", headers=auth_headers(token), timeout=30)
        test("GET /decisions returns 200", r.status_code == 200, f"Got {r.status_code}")
    except Exception as e:
        test("GET /decisions returns 200", False, str(e))

    try:
        r = httpx.get(f"{BASE_URL}/commitments", headers=auth_headers(token), timeout=30)
        test("GET /commitments returns 200", r.status_code == 200, f"Got {r.status_code}")
    except Exception as e:
        test("GET /commitments returns 200", False, str(e))

    try:
        r = httpx.get(f"{BASE_URL}/followups", headers=auth_headers(token), timeout=30)
        test("GET /followups returns 200", r.status_code == 200, f"Got {r.status_code}")
    except Exception as e:
        test("GET /followups returns 200", False, str(e))

    try:
        r = httpx.get(f"{BASE_URL}/audit", headers=auth_headers(token), timeout=30)
        test("GET /audit returns 200", r.status_code == 200, f"Got {r.status_code}")
    except Exception as e:
        test("GET /audit returns 200", False, str(e))

    try:
        r = httpx.get(f"{BASE_URL}/notifications", headers=auth_headers(token), timeout=30)
        test("GET /notifications returns 200", r.status_code == 200, f"Got {r.status_code}")
    except Exception as e:
        test("GET /notifications returns 200", False, str(e))
else:
    for _ in range(8):
        test("Memory/spaces/etc endpoint", False, "No token")

print()

# ============================================================================
# 16. MEETINGS CREATE/GET/SHARE/NOTES/ASK
# ============================================================================
print("16. MEETINGS CREATE/GET/SHARE/NOTES/ASK")
print("-" * 80)

meeting_id = None
if token:
    try:
        r = httpx.get(f"{BASE_URL}/meetings", headers=auth_headers(token), timeout=30)
        test("GET /meetings returns 200", r.status_code == 200, f"Got {r.status_code}")
        if r.status_code == 200 and len(r.json()) > 0:
            meeting_id = r.json()[0].get("id")
    except Exception as e:
        test("GET /meetings returns 200", False, str(e))

    try:
        r = httpx.post(f"{BASE_URL}/meetings", headers=auth_headers(token), json={
            "title": "Test Meeting",
            "mode": "General"
        }, timeout=30)
        test("POST /meetings returns 200", r.status_code == 200, f"Got {r.status_code}")
        if r.status_code == 200:
            meeting_id = r.json().get("id")
    except Exception as e:
        test("POST /meetings returns 200", False, str(e))

    if meeting_id:
        try:
            r = httpx.get(f"{BASE_URL}/meetings/{meeting_id}", headers=auth_headers(token), timeout=30)
            test("GET /meetings/{mid} returns 200", r.status_code == 200, f"Got {r.status_code}")
        except Exception as e:
            test("GET /meetings/{mid} returns 200", False, str(e))

        try:
            r = httpx.post(f"{BASE_URL}/meetings/{meeting_id}/share", headers=auth_headers(token), timeout=30)
            test("POST /meetings/{mid}/share returns 200", r.status_code == 200, f"Got {r.status_code}")
            if r.status_code == 200:
                test("Meeting share returns URL", "url" in r.json(), f"Keys: {list(r.json().keys())}")
        except Exception as e:
            test("POST /meetings/{mid}/share returns 200", False, str(e))
            test("Meeting share returns URL", False, str(e))

        try:
            r = httpx.post(f"{BASE_URL}/meetings/{meeting_id}/notes", headers=auth_headers(token), timeout=60)
            test("POST /meetings/{mid}/notes returns 200", r.status_code == 200, f"Got {r.status_code}")
        except Exception as e:
            test("POST /meetings/{mid}/notes returns 200", False, str(e))

        try:
            r = httpx.post(f"{BASE_URL}/meetings/{meeting_id}/ask", headers=auth_headers(token), json={
                "question": "What was discussed?"
            }, timeout=60)
            test("POST /meetings/{mid}/ask returns 200", r.status_code == 200, f"Got {r.status_code}")
        except Exception as e:
            test("POST /meetings/{mid}/ask returns 200", False, str(e))
    else:
        for _ in range(5):
            test("Meeting endpoint", False, "No meeting ID")
else:
    for _ in range(7):
        test("Meeting endpoint", False, "No token")

print()

# ============================================================================
# 17. AGENTS/REPRESENTATIVE
# ============================================================================
print("17. AGENTS/REPRESENTATIVE")
print("-" * 80)

if token:
    try:
        r = httpx.get(f"{BASE_URL}/agents/marketplace", headers=auth_headers(token), timeout=30)
        test("GET /agents/marketplace returns 200", r.status_code == 200, f"Got {r.status_code}")
        test("Marketplace returns array", isinstance(r.json(), list), f"Got type: {type(r.json())}")
    except Exception as e:
        test("GET /agents/marketplace returns 200", False, str(e))
        test("Marketplace returns array", False, str(e))

    try:
        r = httpx.get(f"{BASE_URL}/agents/installed", headers=auth_headers(token), timeout=30)
        test("GET /agents/installed returns 200", r.status_code == 200, f"Got {r.status_code}")
    except Exception as e:
        test("GET /agents/installed returns 200", False, str(e))

    # Test install agent
    agent_id = None
    try:
        r = httpx.post(f"{BASE_URL}/agents/install", headers=auth_headers(token), json={
            "name": "Test Agent",
            "desc": "Test agent description"
        }, timeout=30)
        test("POST /agents/install returns 200", r.status_code == 200, f"Got {r.status_code}")
        if r.status_code == 200:
            agent_id = r.json().get("id")
    except Exception as e:
        test("POST /agents/install returns 200", False, str(e))

    if agent_id:
        try:
            r = httpx.post(f"{BASE_URL}/agents/{agent_id}/toggle", headers=auth_headers(token), timeout=30)
            test("POST /agents/{aid}/toggle returns 200", r.status_code == 200, f"Got {r.status_code}")
        except Exception as e:
            test("POST /agents/{aid}/toggle returns 200", False, str(e))

        try:
            r = httpx.delete(f"{BASE_URL}/agents/{agent_id}", headers=auth_headers(token), timeout=30)
            test("DELETE /agents/{aid} returns 200", r.status_code == 200, f"Got {r.status_code}")
        except Exception as e:
            test("DELETE /agents/{aid} returns 200", False, str(e))

    try:
        r = httpx.get(f"{BASE_URL}/representative", headers=auth_headers(token), timeout=30)
        test("GET /representative returns 200", r.status_code == 200, f"Got {r.status_code}")
    except Exception as e:
        test("GET /representative returns 200", False, str(e))

    try:
        r = httpx.put(f"{BASE_URL}/representative", headers=auth_headers(token), json={
            "mode": "AI Representative",
            "instructions": "Test instructions"
        }, timeout=30)
        test("PUT /representative returns 200", r.status_code == 200, f"Got {r.status_code}")
    except Exception as e:
        test("PUT /representative returns 200", False, str(e))
else:
    for _ in range(8):
        test("Agent/representative endpoint", False, "No token")

print()

# ============================================================================
# 18. VOICE/TRANSLATION INCLUDING FRIENDLY FAILURE CASES
# ============================================================================
print("18. VOICE/TRANSLATION INCLUDING FRIENDLY FAILURE CASES")
print("-" * 80)

if token:
    # Test transcribe with empty audio
    try:
        empty_file = httpx._multipart.DataField(name="file", value=b"")
        r = httpx.post(f"{BASE_URL}/voice/transcribe", headers=auth_headers(token), data={"language_code": "hi-IN", "mode": "codemix"}, files={"file": ("empty.m4a", b"", "audio/mp4")}, timeout=30)
        test("POST /voice/transcribe with empty audio returns 413", r.status_code == 413, f"Got {r.status_code}")
        test("Empty audio error is friendly", "empty" in r.text.lower() or "recording" in r.text.lower(), f"Got: {r.text[:200]}")
    except Exception as e:
        test("POST /voice/transcribe with empty audio returns 413", False, str(e))
        test("Empty audio error is friendly", False, str(e))

    # Test translate with valid input
    try:
        r = httpx.post(f"{BASE_URL}/translate", headers=auth_headers(token), json={
            "text": "Hello, how are you?",
            "source": "en-IN",
            "target": "hi-IN"
        }, timeout=30)
        test("POST /translate returns 200 or friendly error", r.status_code in [200, 502, 503], f"Got {r.status_code}")
        if r.status_code == 200:
            test("Translate returns translated text", "translated_text" in r.json() or "output" in r.json(), f"Keys: {list(r.json().keys())}")
    except Exception as e:
        test("POST /translate returns 200 or friendly error", False, str(e))
        test("Translate returns translated text", False, str(e))

    # Test translate with source==target
    try:
        r = httpx.post(f"{BASE_URL}/translate", headers=auth_headers(token), json={
            "text": "Hello",
            "source": "en-IN",
            "target": "en-IN"
        }, timeout=30)
        test("POST /translate with source==target returns 400", r.status_code == 400, f"Got {r.status_code}")
    except Exception as e:
        test("POST /translate with source==target returns 400", False, str(e))
else:
    for _ in range(5):
        test("Voice/translation endpoint", False, "No token")

print()

# ============================================================================
# 19. GOOGLE/GMAIL/FCM/ANALYTICS/FEEDBACK ENDPOINTS WITH MISSING CREDENTIALS
# ============================================================================
print("19. GOOGLE/GMAIL/FCM/ANALYTICS/FEEDBACK ENDPOINTS WITH MISSING CREDENTIALS")
print("-" * 80)

if token:
    # Test Google config
    try:
        r = httpx.get(f"{BASE_URL}/auth/google/config", timeout=30)
        test("GET /auth/google/config returns 200", r.status_code == 200, f"Got {r.status_code}")
        test("Google config shows configured status", "configured" in r.json(), f"Keys: {list(r.json().keys())}")
    except Exception as e:
        test("GET /auth/google/config returns 200", False, str(e))
        test("Google config shows configured status", False, str(e))

    # Test Google authorize (should fail gracefully without credentials)
    try:
        r = httpx.get(f"{BASE_URL}/auth/google/authorize", headers=auth_headers(token), timeout=30)
        test("GET /auth/google/authorize returns safe error", r.status_code in [503, 200], f"Got {r.status_code}")
        if r.status_code == 503:
            test("Google authorize error is friendly", "not configured" in r.text.lower() or "unavailable" in r.text.lower(), f"Got: {r.text[:200]}")
    except Exception as e:
        test("GET /auth/google/authorize returns safe error", False, str(e))
        test("Google authorize error is friendly", False, str(e))

    # Test Gmail sync (should fail gracefully without connected account)
    try:
        r = httpx.post(f"{BASE_URL}/gmail/sync", headers=auth_headers(token), timeout=30)
        test("POST /gmail/sync returns safe error", r.status_code in [400, 503], f"Got {r.status_code}")
        test("Gmail sync error is friendly", "connect" in r.text.lower() or "account" in r.text.lower(), f"Got: {r.text[:200]}")
    except Exception as e:
        test("POST /gmail/sync returns safe error", False, str(e))
        test("Gmail sync error is friendly", False, str(e))

    # Test push token registration
    try:
        r = httpx.post(f"{BASE_URL}/push/register", headers=auth_headers(token), json={
            "token": "a" * 50,
            "platform": "android"
        }, timeout=30)
        test("POST /push/register returns 200", r.status_code == 200, f"Got {r.status_code}")
        test("Push register returns registered=true", r.json().get("registered") == True, f"Got: {r.json()}")
    except Exception as e:
        test("POST /push/register returns 200", False, str(e))
        test("Push register returns registered=true", False, str(e))

    # Test push token validation (short token)
    try:
        r = httpx.post(f"{BASE_URL}/push/register", headers=auth_headers(token), json={
            "token": "short",
            "platform": "android"
        }, timeout=30)
        test("POST /push/register with short token returns 422", r.status_code == 422, f"Got {r.status_code}")
    except Exception as e:
        test("POST /push/register with short token returns 422", False, str(e))

    # Test analytics
    try:
        r = httpx.post(f"{BASE_URL}/analytics", headers=auth_headers(token), json={
            "name": "test_event",
            "params": {"key": "value"}
        }, timeout=30)
        test("POST /analytics returns 200", r.status_code == 200, f"Got {r.status_code}")
        test("Analytics returns recorded=true", r.json().get("recorded") == True, f"Got: {r.json()}")
    except Exception as e:
        test("POST /analytics returns 200", False, str(e))
        test("Analytics returns recorded=true", False, str(e))

    # Test feedback (should fail gracefully without Resend)
    try:
        r = httpx.post(f"{BASE_URL}/feedback", headers=auth_headers(token), json={
            "message": "Test feedback message",
            "category": "general"
        }, timeout=30)
        test("POST /feedback returns safe error", r.status_code in [503, 200], f"Got {r.status_code}")
        if r.status_code == 503:
            test("Feedback error is friendly", "unavailable" in r.text.lower() or "temporarily" in r.text.lower(), f"Got: {r.text[:200]}")
    except Exception as e:
        test("POST /feedback returns safe error", False, str(e))
        test("Feedback error is friendly", False, str(e))
else:
    for _ in range(12):
        test("Google/Gmail/FCM/analytics/feedback endpoint", False, "No token")

print()

# ============================================================================
# 20. NETWORK/INVALID-AUTH/VALIDATION ERRORS
# ============================================================================
print("20. NETWORK/INVALID-AUTH/VALIDATION ERRORS")
print("-" * 80)

# Test invalid auth on protected endpoint
try:
    r = httpx.get(f"{BASE_URL}/dashboard", headers={"Authorization": "Bearer invalid_token"}, timeout=30)
    test("Protected endpoint with invalid token returns 401", r.status_code == 401, f"Got {r.status_code}")
except Exception as e:
    test("Protected endpoint with invalid token returns 401", False, str(e))

# Test validation error on compose (missing required fields)
if token:
    try:
        r = httpx.post(f"{BASE_URL}/emails/compose", headers=auth_headers(token), json={
            "subject": "Test"
            # Missing required 'to' and 'body' fields
        }, timeout=30)
        test("POST /emails/compose with missing fields returns 422", r.status_code == 422, f"Got {r.status_code}")
    except Exception as e:
        test("POST /emails/compose with missing fields returns 422", False, str(e))

# Test search
if token:
    try:
        r = httpx.get(f"{BASE_URL}/search?q=test", headers=auth_headers(token), timeout=30)
        test("GET /search returns 200", r.status_code == 200, f"Got {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            test("Search returns multiple categories", "emails" in data and "tasks" in data, f"Keys: {list(data.keys())}")
    except Exception as e:
        test("GET /search returns 200", False, str(e))
        test("Search returns multiple categories", False, str(e))

print()

# ============================================================================
# SUMMARY
# ============================================================================
print("=" * 80)
print("TEST SUMMARY")
print("=" * 80)
print(f"Total tests: {passed + failed}")
print(f"Passed: {passed}")
print(f"Failed: {failed}")
print()

if failed > 0:
    print("FAILURES:")
    print("-" * 80)
    for failure in failures:
        print(f"  ✗ {failure}")
    print()
    sys.exit(1)
else:
    print("✓ ALL TESTS PASSED")
    sys.exit(0)
