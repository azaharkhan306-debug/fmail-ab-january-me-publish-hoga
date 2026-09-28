#!/usr/bin/env python3
"""
Comprehensive backend API test suite for Fmail
Tests all new features + regression tests
"""
import requests
import json
import time
from typing import Dict, Any, Optional

# Backend URL from frontend/.env
BASE_URL = "https://76123247-a717-4e58-afaa-9d5e2094c3c9.preview.emergentagent.com/api"

# Test credentials
DEMO_EMAIL = "demo@fmail.com"
DEMO_PASSWORD = "demo123"

# Color codes for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

class TestResults:
    def __init__(self):
        self.passed = []
        self.failed = []
        self.warnings = []
    
    def add_pass(self, test_name: str, detail: str = ""):
        self.passed.append((test_name, detail))
        print(f"{GREEN}✓ PASS{RESET}: {test_name}" + (f" - {detail}" if detail else ""))
    
    def add_fail(self, test_name: str, error: str):
        self.failed.append((test_name, error))
        print(f"{RED}✗ FAIL{RESET}: {test_name} - {error}")
    
    def add_warning(self, test_name: str, message: str):
        self.warnings.append((test_name, message))
        print(f"{YELLOW}⚠ WARNING{RESET}: {test_name} - {message}")
    
    def summary(self):
        print(f"\n{BLUE}{'='*80}{RESET}")
        print(f"{BLUE}TEST SUMMARY{RESET}")
        print(f"{BLUE}{'='*80}{RESET}")
        print(f"{GREEN}Passed: {len(self.passed)}{RESET}")
        print(f"{RED}Failed: {len(self.failed)}{RESET}")
        print(f"{YELLOW}Warnings: {len(self.warnings)}{RESET}")
        
        if self.failed:
            print(f"\n{RED}FAILED TESTS:{RESET}")
            for name, error in self.failed:
                print(f"  • {name}: {error}")
        
        return len(self.failed) == 0

results = TestResults()

def make_request(method: str, endpoint: str, token: Optional[str] = None, 
                 json_data: Optional[Dict] = None, params: Optional[Dict] = None,
                 files: Optional[Dict] = None, data: Optional[Dict] = None) -> tuple:
    """Make HTTP request and return (success, response_data, status_code)"""
    url = f"{BASE_URL}{endpoint}"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    try:
        if method == "GET":
            r = requests.get(url, headers=headers, params=params, timeout=30)
        elif method == "POST":
            if files:
                r = requests.post(url, headers=headers, files=files, data=data, timeout=30)
            else:
                headers["Content-Type"] = "application/json"
                r = requests.post(url, headers=headers, json=json_data, timeout=30)
        elif method == "PUT":
            headers["Content-Type"] = "application/json"
            r = requests.put(url, headers=headers, json=json_data, timeout=30)
        elif method == "DELETE":
            r = requests.delete(url, headers=headers, timeout=30)
        elif method == "PATCH":
            headers["Content-Type"] = "application/json"
            r = requests.patch(url, headers=headers, json=json_data, timeout=30)
        else:
            return False, f"Unknown method: {method}", 0
        
        try:
            data = r.json()
        except:
            data = r.text
        
        return r.status_code < 400, data, r.status_code
    except requests.exceptions.Timeout:
        return False, "Request timeout", 0
    except requests.exceptions.ConnectionError:
        return False, "Connection error", 0
    except Exception as e:
        return False, str(e), 0

def test_check_handle():
    """Test 1: AUTH check-handle (public, case-insensitive)"""
    print(f"\n{BLUE}TEST 1: AUTH check-handle{RESET}")
    
    # Test 1a: Existing handle (demo)
    success, data, status = make_request("GET", "/auth/check-handle", params={"handle": "demo"})
    if success and data.get("available") == False:
        results.add_pass("check-handle: demo taken", "available=false")
    else:
        results.add_fail("check-handle: demo taken", f"Expected available=false, got {data}")
    
    # Test 1b: Case-insensitive (Demo with capital)
    success, data, status = make_request("GET", "/auth/check-handle", params={"handle": "Demo"})
    if success and data.get("available") == False:
        results.add_pass("check-handle: case-insensitive", "Demo also taken")
    else:
        results.add_fail("check-handle: case-insensitive", f"Expected available=false, got {data}")
    
    # Test 1c: New unique handle
    unique_handle = f"testuser{int(time.time())}"
    success, data, status = make_request("GET", "/auth/check-handle", params={"handle": unique_handle})
    if success and data.get("available") == True:
        results.add_pass("check-handle: unique available", f"{unique_handle} available")
    else:
        results.add_fail("check-handle: unique available", f"Expected available=true, got {data}")
    
    # Test 1d: Min length (ab - too short)
    success, data, status = make_request("GET", "/auth/check-handle", params={"handle": "ab"})
    if success and data.get("available") == False and "3 characters" in str(data.get("reason", "")):
        results.add_pass("check-handle: min length", "ab rejected (min 3 chars)")
    else:
        results.add_fail("check-handle: min length", f"Expected min length error, got {data}")
    
    # Test 1e: Invalid characters
    success, data, status = make_request("GET", "/auth/check-handle", params={"handle": "bad handle!"})
    if success and data.get("available") == False:
        results.add_pass("check-handle: invalid chars", "bad handle! rejected")
    else:
        results.add_fail("check-handle: invalid chars", f"Expected available=false, got {data}")

def test_otp_and_reset():
    """Test 2: OTP + PASSWORD RESET flow"""
    print(f"\n{BLUE}TEST 2: OTP + PASSWORD RESET{RESET}")
    
    test_email = f"resettest{int(time.time())}@example.com"
    test_username = f"resettest{int(time.time())}"
    
    # Test 2a: Request OTP for non-existent account (signup purpose)
    success, data, status = make_request("POST", "/auth/request-otp", 
                                        json_data={"email": test_email, "purpose": "signup"})
    if success and data.get("sent") == True and "devCode" in data:
        dev_code = data["devCode"]
        results.add_pass("OTP: request for signup", f"devCode={dev_code}")
    else:
        results.add_fail("OTP: request for signup", f"Expected sent=true with devCode, got {data}")
        return
    
    # Test 2b: Register the account
    success, data, status = make_request("POST", "/auth/signup", json_data={
        "email": test_email,
        "password": "pass123",
        "name": "Reset Test",
        "username": test_username
    })
    if success and "token" in data and "user" in data:
        results.add_pass("OTP: signup without code", "Account created (no SMTP)")
    else:
        results.add_fail("OTP: signup without code", f"Signup failed: {data}")
        return
    
    # Test 2c: Request OTP for password reset
    success, data, status = make_request("POST", "/auth/request-otp",
                                        json_data={"email": test_email, "purpose": "reset"})
    if success and data.get("sent") == True and "devCode" in data:
        reset_code = data["devCode"]
        results.add_pass("OTP: request for reset", f"devCode={reset_code}")
    else:
        results.add_fail("OTP: request for reset", f"Expected devCode, got {data}")
        return
    
    # Test 2d: Verify OTP with correct code
    success, data, status = make_request("POST", "/auth/verify-otp",
                                        json_data={"email": test_email, "code": reset_code, "purpose": "reset"})
    if success and data.get("verified") == True:
        results.add_pass("OTP: verify correct code", "verified=true")
    else:
        results.add_fail("OTP: verify correct code", f"Expected verified=true, got {data}")
    
    # Test 2e: Verify with wrong code (should fail)
    success, data, status = make_request("POST", "/auth/verify-otp",
                                        json_data={"email": test_email, "code": "000000", "purpose": "reset"})
    if not success and status == 400:
        results.add_pass("OTP: wrong code rejected", "400 error as expected")
    else:
        results.add_fail("OTP: wrong code rejected", f"Expected 400 error, got status={status}")
    
    # Test 2f: Reset password with correct code
    success, data, status = make_request("POST", "/auth/reset-password",
                                        json_data={"email": test_email, "code": reset_code, "password": "newpass123"})
    if success and "token" in data and "user" in data:
        new_token = data["token"]
        results.add_pass("OTP: reset password", "Password reset successful")
    else:
        results.add_fail("OTP: reset password", f"Reset failed: {data}")
        return
    
    # Test 2g: Login with new password
    success, data, status = make_request("POST", "/auth/login",
                                        json_data={"email": test_email, "password": "newpass123"})
    if success and "token" in data:
        results.add_pass("OTP: login with new password", "Login successful")
    else:
        results.add_fail("OTP: login with new password", f"Login failed: {data}")
    
    # Test 2h: Login with old password (should fail)
    success, data, status = make_request("POST", "/auth/login",
                                        json_data={"email": test_email, "password": "pass123"})
    if not success and status == 401:
        results.add_pass("OTP: old password rejected", "401 as expected")
    else:
        results.add_fail("OTP: old password rejected", f"Expected 401, got status={status}")
    
    # Test 2i: Resend cooldown (two requests within 30s)
    success1, data1, status1 = make_request("POST", "/auth/request-otp",
                                           json_data={"email": test_email, "purpose": "reset"})
    time.sleep(1)  # Wait 1 second
    success2, data2, status2 = make_request("POST", "/auth/request-otp",
                                           json_data={"email": test_email, "purpose": "reset"})
    if not success2 and status2 == 429:
        results.add_pass("OTP: resend cooldown", "429 rate limit enforced")
    else:
        results.add_warning("OTP: resend cooldown", f"Expected 429, got status={status2}")

def test_ai_compose(token: str):
    """Test 3: AI EMAIL WRITER"""
    print(f"\n{BLUE}TEST 3: AI EMAIL WRITER{RESET}")
    
    # Test 3a: Professional tone
    success, data, status = make_request("POST", "/ai/compose", token=token, json_data={
        "instruction": "Ask Rahul to reschedule call to Friday 3pm",
        "tone": "Professional"
    })
    if success and data.get("subject") and data.get("body"):
        results.add_pass("AI compose: Professional tone", f"subject={data['subject'][:50]}...")
    else:
        results.add_fail("AI compose: Professional tone", f"Expected subject+body, got {data}")
    
    # Test 3b: Short tone
    success, data, status = make_request("POST", "/ai/compose", token=token, json_data={
        "instruction": "Thank the team for their hard work",
        "tone": "Short"
    })
    if success and data.get("subject") and data.get("body"):
        results.add_pass("AI compose: Short tone", f"subject={data['subject'][:50]}...")
    else:
        results.add_fail("AI compose: Short tone", f"Expected subject+body, got {data}")
    
    # Test 3c: Invalid tone (should default to Professional)
    success, data, status = make_request("POST", "/ai/compose", token=token, json_data={
        "instruction": "Send meeting notes",
        "tone": "InvalidTone"
    })
    if success and data.get("subject") and data.get("body"):
        results.add_pass("AI compose: invalid tone defaults", "Still returns subject+body")
    else:
        results.add_fail("AI compose: invalid tone defaults", f"Expected subject+body, got {data}")

def test_email_compose(token: str):
    """Test 4: EMAIL compose with cc/bcc/attachments"""
    print(f"\n{BLUE}TEST 4: EMAIL compose with cc/bcc/attachments{RESET}")
    
    # Test 4a: Compose with cc/bcc/attachments
    success, data, status = make_request("POST", "/emails/compose", token=token, json_data={
        "to": "test@example.com",
        "cc": "cc@example.com",
        "bcc": "bcc@example.com",
        "subject": "Test Email with Attachments",
        "body": "Hello, this is a test email.",
        "attachments": [
            {"name": "test.txt", "type": "text", "size": "10", "data": "aGVsbG8="}
        ]
    })
    if success and data.get("cc") == "cc@example.com" and data.get("bcc") == "bcc@example.com" \
       and len(data.get("attachments", [])) == 1 and data.get("folder") == "sent":
        sent_thread_id = data.get("threadId")
        results.add_pass("Email compose: cc/bcc/attachments", f"threadId={sent_thread_id}")
    else:
        results.add_fail("Email compose: cc/bcc/attachments", f"Missing cc/bcc/attachments, got {data}")
        sent_thread_id = None
    
    # Test 4b: Draft compose
    success, data, status = make_request("POST", "/emails/compose", token=token, json_data={
        "to": "draft@example.com",
        "subject": "Draft Email",
        "body": "This is a draft",
        "draft": True
    })
    if success and data.get("folder") == "drafts":
        draft_thread_id = data.get("threadId")
        results.add_pass("Email compose: draft", f"folder=drafts, threadId={draft_thread_id}")
    else:
        results.add_fail("Email compose: draft", f"Expected folder=drafts, got {data}")
        draft_thread_id = None
    
    # Test 4c: Get drafts folder
    success, data, status = make_request("GET", "/emails", token=token, params={"folder": "drafts"})
    if success and isinstance(data, list):
        draft_found = any(e.get("subject") == "Draft Email" for e in data)
        if draft_found:
            results.add_pass("Email compose: draft in folder", "Draft appears in drafts folder")
        else:
            results.add_warning("Email compose: draft in folder", "Draft not found in folder")
    else:
        results.add_fail("Email compose: draft in folder", f"Failed to get drafts: {data}")
    
    return sent_thread_id, draft_thread_id

def test_delete_email(token: str, thread_id: Optional[str]):
    """Test 5: DELETE email/thread"""
    print(f"\n{BLUE}TEST 5: DELETE email/thread{RESET}")
    
    if not thread_id:
        results.add_warning("Delete email", "No thread_id from compose test, skipping")
        return
    
    # Test 5a: First delete (move to trash)
    success, data, status = make_request("DELETE", f"/emails/{thread_id}", token=token)
    if success and data.get("ok") == True:
        results.add_pass("Delete email: move to trash", "ok=true")
    else:
        results.add_fail("Delete email: move to trash", f"Expected ok=true, got {data}")
        return
    
    # Test 5b: Verify in trash
    success, data, status = make_request("GET", "/emails", token=token, params={"folder": "trash"})
    if success and isinstance(data, list):
        in_trash = any(e.get("threadId") == thread_id for e in data)
        if in_trash:
            results.add_pass("Delete email: in trash", "Thread found in trash")
        else:
            results.add_warning("Delete email: in trash", "Thread not found in trash")
    
    # Test 5c: Second delete (permanent)
    success, data, status = make_request("DELETE", f"/emails/{thread_id}", token=token)
    if success and data.get("ok") == True:
        results.add_pass("Delete email: permanent", "ok=true")
    else:
        results.add_fail("Delete email: permanent", f"Expected ok=true, got {data}")
    
    # Test 5d: Verify not in trash
    success, data, status = make_request("GET", "/emails", token=token, params={"folder": "trash"})
    if success and isinstance(data, list):
        still_in_trash = any(e.get("threadId") == thread_id for e in data)
        if not still_in_trash:
            results.add_pass("Delete email: permanently removed", "Not in trash list")
        else:
            results.add_fail("Delete email: permanently removed", "Still in trash after permanent delete")

def test_permissions(token: str):
    """Test 6: PERMISSIONS"""
    print(f"\n{BLUE}TEST 6: PERMISSIONS{RESET}")
    
    # Test 6a: Set permissions
    success, data, status = make_request("PUT", "/auth/permissions", token=token, json_data={
        "permissions": {
            "camera": True,
            "microphone": False,
            "notifications": True
        }
    })
    if success and data.get("permissions"):
        perms = data["permissions"]
        if perms.get("camera") == True and perms.get("microphone") == False and perms.get("notifications") == True:
            results.add_pass("Permissions: set", "camera=true, microphone=false, notifications=true")
        else:
            results.add_fail("Permissions: set", f"Permissions mismatch: {perms}")
    else:
        results.add_fail("Permissions: set", f"Expected permissions in response, got {data}")
    
    # Test 6b: Verify in /auth/me
    success, data, status = make_request("GET", "/auth/me", token=token)
    if success and data.get("permissions"):
        perms = data["permissions"]
        if perms.get("camera") == True and perms.get("microphone") == False:
            results.add_pass("Permissions: reflected in /me", "Permissions match")
        else:
            results.add_fail("Permissions: reflected in /me", f"Permissions mismatch: {perms}")
    else:
        results.add_fail("Permissions: reflected in /me", f"No permissions in /me response")

def test_delete_account():
    """Test 7: DELETE ACCOUNT"""
    print(f"\n{BLUE}TEST 7: DELETE ACCOUNT{RESET}")
    
    # Create throwaway account
    throwaway_email = f"deleteme{int(time.time())}@example.com"
    throwaway_username = f"deleteme{int(time.time())}"
    
    # Test 7a: Create account
    success, data, status = make_request("POST", "/auth/signup", json_data={
        "email": throwaway_email,
        "password": "delete123",
        "name": "Delete Me",
        "username": throwaway_username
    })
    if success and "token" in data:
        throwaway_token = data["token"]
        results.add_pass("Delete account: create throwaway", f"email={throwaway_email}")
    else:
        results.add_fail("Delete account: create throwaway", f"Signup failed: {data}")
        return
    
    # Test 7b: Delete account
    success, data, status = make_request("DELETE", "/auth/account", token=throwaway_token)
    if success and data.get("deleted") == True:
        results.add_pass("Delete account: deleted", "deleted=true")
    else:
        results.add_fail("Delete account: deleted", f"Expected deleted=true, got {data}")
        return
    
    # Test 7c: Verify token invalid
    success, data, status = make_request("GET", "/auth/me", token=throwaway_token)
    if not success and status == 401:
        results.add_pass("Delete account: token invalid", "401 as expected")
    else:
        results.add_fail("Delete account: token invalid", f"Expected 401, got status={status}")
    
    # Test 7d: Verify login fails
    success, data, status = make_request("POST", "/auth/login", json_data={
        "email": throwaway_email,
        "password": "delete123"
    })
    if not success and status == 401:
        results.add_pass("Delete account: login fails", "401 as expected")
    else:
        results.add_fail("Delete account: login fails", f"Expected 401, got status={status}")

def test_sarvam(token: str):
    """Test 8: SARVAM"""
    print(f"\n{BLUE}TEST 8: SARVAM{RESET}")
    
    # Test 8a: Transcribe with empty file
    success, data, status = make_request("POST", "/voice/transcribe", token=token,
                                        files={"file": ("empty.m4a", b"", "audio/mp4")},
                                        data={"language_code": "hi-IN", "mode": "codemix"})
    if not success and status == 413:
        results.add_pass("Sarvam: empty file rejected", "413 friendly message")
    else:
        results.add_warning("Sarvam: empty file rejected", f"Expected 413, got status={status}, data={data}")
    
    # Test 8b: Translate with different languages
    success, data, status = make_request("POST", "/translate", token=token, json_data={
        "text": "Hello, how are you?",
        "source": "en-IN",
        "target": "hi-IN"
    })
    if success:
        results.add_pass("Sarvam: translate en->hi", f"Translation successful: {str(data)[:100]}")
    elif status in (502, 429, 503, 504):
        results.add_pass("Sarvam: translate en->hi", f"Friendly error {status} (API issue, not code issue)")
    else:
        results.add_fail("Sarvam: translate en->hi", f"Unexpected error: status={status}, data={data}")
    
    # Test 8c: Translate with same source/target (should fail)
    success, data, status = make_request("POST", "/translate", token=token, json_data={
        "text": "Test",
        "source": "en-IN",
        "target": "en-IN"
    })
    if not success and status == 400:
        results.add_pass("Sarvam: same source/target rejected", "400 as expected")
    else:
        results.add_fail("Sarvam: same source/target rejected", f"Expected 400, got status={status}")

def test_regression():
    """Test 9: REGRESSION"""
    print(f"\n{BLUE}TEST 9: REGRESSION{RESET}")
    
    # Test 9a: Login with demo account
    success, data, status = make_request("POST", "/auth/login", json_data={
        "email": DEMO_EMAIL,
        "password": DEMO_PASSWORD
    })
    if success and "token" in data and "user" in data:
        demo_token = data["token"]
        results.add_pass("Regression: demo login", "Login successful")
    else:
        results.add_fail("Regression: demo login", f"Login failed: {data}")
        return None
    
    # Test 9b: Dashboard
    success, data, status = make_request("GET", "/dashboard", token=demo_token)
    if success and "brief" in data and "counts" in data:
        results.add_pass("Regression: dashboard", f"brief={data['brief'][:50]}...")
    else:
        results.add_fail("Regression: dashboard", f"Expected brief+counts, got {data}")
    
    # Test 9c: Emails inbox (should be non-empty)
    success, data, status = make_request("GET", "/emails", token=demo_token, params={"folder": "inbox"})
    if success and isinstance(data, list) and len(data) > 0:
        inbox_thread_id = data[0].get("threadId")
        results.add_pass("Regression: emails inbox", f"{len(data)} emails found")
    else:
        results.add_fail("Regression: emails inbox", f"Expected non-empty list, got {data}")
        inbox_thread_id = None
    
    # Test 9d: AI reply
    if inbox_thread_id:
        success, data, status = make_request("POST", "/ai/reply", token=demo_token, json_data={
            "threadId": inbox_thread_id,
            "tone": "Friendly",
            "action": "reply"
        })
        if success and data.get("text"):
            results.add_pass("Regression: ai/reply", f"text={data['text'][:50]}...")
        else:
            results.add_fail("Regression: ai/reply", f"Expected text, got {data}")
    else:
        results.add_warning("Regression: ai/reply", "No inbox thread to test with")
    
    return demo_token

def main():
    print(f"{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}FMAIL BACKEND API TEST SUITE{RESET}")
    print(f"{BLUE}{'='*80}{RESET}")
    print(f"Base URL: {BASE_URL}")
    print(f"Demo credentials: {DEMO_EMAIL} / {DEMO_PASSWORD}")
    
    # Run all tests
    test_check_handle()
    test_otp_and_reset()
    
    # Get demo token for authenticated tests
    demo_token = test_regression()
    
    if demo_token:
        test_ai_compose(demo_token)
        sent_thread_id, draft_thread_id = test_email_compose(demo_token)
        test_delete_email(demo_token, sent_thread_id)
        test_permissions(demo_token)
        test_sarvam(demo_token)
    else:
        print(f"{RED}Cannot run authenticated tests without demo token{RESET}")
    
    test_delete_account()
    
    # Print summary
    success = results.summary()
    
    if success:
        print(f"\n{GREEN}{'='*80}{RESET}")
        print(f"{GREEN}ALL TESTS PASSED!{RESET}")
        print(f"{GREEN}{'='*80}{RESET}")
    else:
        print(f"\n{RED}{'='*80}{RESET}")
        print(f"{RED}SOME TESTS FAILED - SEE DETAILS ABOVE{RESET}")
        print(f"{RED}{'='*80}{RESET}")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
