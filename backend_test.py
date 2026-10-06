#!/usr/bin/env python3
"""
Comprehensive backend test for Fmail Gmail client conversion.
Tests all endpoints with focus on identity removal, Google OAuth, Gmail integration, and local fallback.
"""
import requests
import json
import secrets
from typing import Dict, Any, Optional

# Backend URL from frontend/.env
BASE_URL = "https://156b1505-8090-42e9-aeff-8a71243aec71.preview.emergentagent.com/api"

# Demo account credentials (has NO Gmail connected)
DEMO_EMAIL = "demo@fmail.com"
DEMO_PASSWORD = "demo123"

# Test results tracking
passed = 0
failed = 0
failures = []

def log_test(name: str, success: bool, details: str = ""):
    global passed, failed, failures
    if success:
        passed += 1
        print(f"✅ PASS: {name}")
        if details:
            print(f"   {details}")
    else:
        failed += 1
        failures.append(f"{name}: {details}")
        print(f"❌ FAIL: {name}")
        print(f"   {details}")

def check_no_secrets(data: Any, test_name: str) -> bool:
    """Verify no secrets are leaked in response."""
    text = json.dumps(data) if isinstance(data, (dict, list)) else str(data)
    secrets_found = []
    
    # Check for Google client secret
    if "GOCSPX" in text:
        secrets_found.append("Google client secret (GOCSPX)")
    
    # Check for Firebase private key
    if "BEGIN PRIVATE KEY" in text or "private_key" in text.lower():
        secrets_found.append("Firebase private key")
    
    # Check for JWT secret
    if "fmail-local-development-session-secret" in text:
        secrets_found.append("JWT secret")
    
    # Check for OTP codes (6 digits)
    if "devCode" in text or "testCode" in text:
        secrets_found.append("OTP test code")
    
    if secrets_found:
        log_test(f"Security check: {test_name}", False, f"LEAKED SECRETS: {', '.join(secrets_found)}")
        return False
    return True

def test_root():
    """Test 1: GET /api/ returns 200 {status: ok}"""
    try:
        resp = requests.get(f"{BASE_URL}/", timeout=10)
        data = resp.json()
        
        success = resp.status_code == 200 and data.get("status") == "ok"
        log_test("GET /api/ returns 200 with status=ok", success, 
                f"Status: {resp.status_code}, Response: {data}")
        check_no_secrets(data, "root endpoint")
        return success
    except Exception as e:
        log_test("GET /api/ returns 200 with status=ok", False, str(e))
        return False

def test_check_handle_removed():
    """Test 2.1: GET /api/auth/check-handle?handle=demo returns 404 (endpoint removed)"""
    try:
        resp = requests.get(f"{BASE_URL}/auth/check-handle", params={"handle": "demo"}, timeout=10)
        
        success = resp.status_code == 404
        log_test("GET /auth/check-handle returns 404 (endpoint removed)", success,
                f"Status: {resp.status_code}")
        if resp.status_code != 404:
            check_no_secrets(resp.text, "check-handle endpoint")
        return success
    except Exception as e:
        log_test("GET /auth/check-handle returns 404 (endpoint removed)", False, str(e))
        return False

def test_signup_no_username():
    """Test 2.2: POST /api/auth/signup with ONLY {email, password, name} (NO username)"""
    try:
        # Generate unique email for throwaway account
        unique_email = f"test_{secrets.token_hex(8)}@throwaway.com"
        
        payload = {
            "email": unique_email,
            "password": "test123456",
            "name": "Test User"
        }
        
        resp = requests.post(f"{BASE_URL}/auth/signup", json=payload, timeout=10)
        data = resp.json()
        
        # Check response structure
        has_token = "token" in data
        has_user = "user" in data
        user = data.get("user", {})
        
        # Critical: user must NOT contain 'handle' or 'fmail' keys
        has_handle = "handle" in user
        has_fmail = "fmail" in user
        has_password = "password" in user
        
        success = (resp.status_code == 200 and has_token and has_user and 
                  not has_handle and not has_fmail and not has_password)
        
        details = f"Status: {resp.status_code}, has_token: {has_token}, has_user: {has_user}, "
        details += f"user_has_handle: {has_handle}, user_has_fmail: {has_fmail}, user_has_password: {has_password}"
        
        if has_handle or has_fmail:
            details += f"\n   ❌ CRITICAL: User object contains forbidden keys! User: {user}"
        
        log_test("Signup without username field succeeds, user has NO handle/fmail", success, details)
        check_no_secrets(data, "signup endpoint")
        
        # Clean up: delete the throwaway account
        if has_token:
            try:
                token = data["token"]
                del_resp = requests.delete(f"{BASE_URL}/auth/account", 
                                          headers={"Authorization": f"Bearer {token}"}, 
                                          timeout=10)
                if del_resp.status_code == 200:
                    print(f"   🗑️  Cleaned up throwaway account: {unique_email}")
            except Exception as cleanup_err:
                print(f"   ⚠️  Failed to cleanup throwaway account: {cleanup_err}")
        
        return success
    except Exception as e:
        log_test("Signup without username field succeeds, user has NO handle/fmail", False, str(e))
        return False

def test_demo_login():
    """Test 2.3: Login demo@fmail.com/demo123 works"""
    try:
        payload = {"email": DEMO_EMAIL, "password": DEMO_PASSWORD}
        resp = requests.post(f"{BASE_URL}/auth/login", json=payload, timeout=10)
        data = resp.json()
        
        has_token = "token" in data
        has_user = "user" in data
        
        success = resp.status_code == 200 and has_token and has_user
        log_test("Demo login (demo@fmail.com/demo123) works", success,
                f"Status: {resp.status_code}, has_token: {has_token}, has_user: {has_user}")
        check_no_secrets(data, "login endpoint")
        
        return data.get("token") if success else None
    except Exception as e:
        log_test("Demo login (demo@fmail.com/demo123) works", False, str(e))
        return None

def test_auth_me(token: str):
    """Test 2.4: GET /api/auth/me returns correct structure"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(f"{BASE_URL}/auth/me", headers=headers, timeout=10)
        data = resp.json()
        
        # Check required fields
        has_gmail_connected = "gmailConnected" in data
        has_gmail_email = "gmailEmail" in data
        has_connected_accounts = "connectedAccounts" in data
        has_password = "password" in data
        
        gmail_connected = data.get("gmailConnected")
        gmail_email = data.get("gmailEmail")
        connected_accounts = data.get("connectedAccounts", [])
        
        # For demo account: gmailConnected should be false, gmailEmail should be null
        correct_gmail_status = gmail_connected == False and gmail_email == None
        
        # connectedAccounts should have gmail provider
        has_gmail_provider = False
        if connected_accounts and len(connected_accounts) > 0:
            has_gmail_provider = any(acc.get("provider") == "gmail" for acc in connected_accounts)
        
        success = (resp.status_code == 200 and has_gmail_connected and has_gmail_email and 
                  has_connected_accounts and not has_password and correct_gmail_status and 
                  has_gmail_provider)
        
        details = f"Status: {resp.status_code}, gmailConnected: {gmail_connected}, "
        details += f"gmailEmail: {gmail_email}, has_password: {has_password}, "
        details += f"connectedAccounts: {connected_accounts}"
        
        log_test("GET /auth/me returns correct structure (no password, gmailConnected=false)", 
                success, details)
        check_no_secrets(data, "auth/me endpoint")
        
        return success
    except Exception as e:
        log_test("GET /auth/me returns correct structure", False, str(e))
        return False

def test_google_config():
    """Test 3.1: GET /api/auth/google/config"""
    try:
        resp = requests.get(f"{BASE_URL}/auth/google/config", timeout=10)
        data = resp.json()
        
        configured = data.get("configured")
        provider = data.get("provider")
        project = data.get("project")
        
        success = (resp.status_code == 200 and configured == True and 
                  provider == "google" and project == "fmail-a296f")
        
        log_test("GET /auth/google/config returns correct structure", success,
                f"Status: {resp.status_code}, configured: {configured}, provider: {provider}, project: {project}")
        check_no_secrets(data, "google/config endpoint")
        
        return success
    except Exception as e:
        log_test("GET /auth/google/config returns correct structure", False, str(e))
        return False

def test_google_login_url():
    """Test 3.2: GET /api/auth/google/login-url (public)"""
    try:
        resp = requests.get(f"{BASE_URL}/auth/google/login-url", timeout=10)
        data = resp.json()
        
        url = data.get("url", "")
        
        has_accounts_google = "accounts.google.com" in url
        has_gmail_modify = "gmail.modify" in url
        has_state = "state=" in url
        
        success = (resp.status_code == 200 and has_accounts_google and 
                  has_gmail_modify and has_state)
        
        log_test("GET /auth/google/login-url returns valid OAuth URL", success,
                f"Status: {resp.status_code}, has_accounts_google: {has_accounts_google}, "
                f"has_gmail_modify: {has_gmail_modify}, has_state: {has_state}")
        check_no_secrets(data, "google/login-url endpoint")
        
        return success
    except Exception as e:
        log_test("GET /auth/google/login-url returns valid OAuth URL", False, str(e))
        return False

def test_google_exchange_invalid():
    """Test 3.3: POST /api/auth/google/exchange with invalid code"""
    try:
        payload = {"code": "invalid"}
        resp = requests.post(f"{BASE_URL}/auth/google/exchange", json=payload, timeout=10)
        
        # Should return 400 with safe error message
        success = resp.status_code == 400
        
        try:
            data = resp.json()
            message = data.get("detail", "")
        except:
            message = resp.text
        
        log_test("POST /auth/google/exchange with invalid code returns 400", success,
                f"Status: {resp.status_code}, Message: {message}")
        check_no_secrets(resp.text, "google/exchange endpoint")
        
        return success
    except Exception as e:
        log_test("POST /auth/google/exchange with invalid code returns 400", False, str(e))
        return False

def test_google_authorize(token: str):
    """Test 3.4: GET /api/auth/google/authorize (authenticated)"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(f"{BASE_URL}/auth/google/authorize", headers=headers, timeout=10)
        data = resp.json()
        
        url = data.get("url", "")
        has_accounts_google = "accounts.google.com" in url
        
        success = resp.status_code == 200 and has_accounts_google
        
        log_test("GET /auth/google/authorize returns OAuth URL", success,
                f"Status: {resp.status_code}, has_accounts_google: {has_accounts_google}")
        check_no_secrets(data, "google/authorize endpoint")
        
        return success
    except Exception as e:
        log_test("GET /auth/google/authorize returns OAuth URL", False, str(e))
        return False

def test_google_disconnect(token: str):
    """Test 3.5: POST /api/auth/google/disconnect"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.post(f"{BASE_URL}/auth/google/disconnect", headers=headers, timeout=10)
        data = resp.json()
        
        connected = data.get("connected")
        
        success = resp.status_code == 200 and connected == False
        
        log_test("POST /auth/google/disconnect returns {connected:false}", success,
                f"Status: {resp.status_code}, connected: {connected}")
        check_no_secrets(data, "google/disconnect endpoint")
        
        return success
    except Exception as e:
        log_test("POST /auth/google/disconnect returns {connected:false}", False, str(e))
        return False

def test_gmail_status(token: str):
    """Test 4.1: GET /api/gmail/status (demo has no Gmail)"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(f"{BASE_URL}/gmail/status", headers=headers, timeout=10)
        data = resp.json()
        
        connected = data.get("connected")
        email = data.get("email")
        needs_reconnect = data.get("needsReconnect")
        
        success = (resp.status_code == 200 and connected == False and 
                  email == None and needs_reconnect == False)
        
        log_test("GET /gmail/status returns correct status for demo account", success,
                f"Status: {resp.status_code}, connected: {connected}, email: {email}, needsReconnect: {needs_reconnect}")
        check_no_secrets(data, "gmail/status endpoint")
        
        return success
    except Exception as e:
        log_test("GET /gmail/status returns correct status for demo account", False, str(e))
        return False

def test_gmail_sync(token: str):
    """Test 4.2: POST /api/gmail/sync (should fail - no Gmail connected)"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.post(f"{BASE_URL}/gmail/sync", headers=headers, timeout=10)
        
        success = resp.status_code == 400
        
        try:
            data = resp.json()
            message = data.get("detail", "")
            has_correct_message = "Connect a Google account" in message
        except:
            message = resp.text
            has_correct_message = "Connect a Google account" in message
        
        log_test("POST /gmail/sync returns 400 with correct message", success and has_correct_message,
                f"Status: {resp.status_code}, Message: {message}")
        check_no_secrets(resp.text, "gmail/sync endpoint")
        
        return success
    except Exception as e:
        log_test("POST /gmail/sync returns 400 with correct message", False, str(e))
        return False

def test_gmail_watch(token: str):
    """Test 4.3: POST /api/gmail/watch (should return 503 - no Pub/Sub topic)"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.post(f"{BASE_URL}/gmail/watch", headers=headers, timeout=10)
        
        success = resp.status_code == 503
        
        try:
            data = resp.json()
            message = data.get("detail", "")
        except:
            message = resp.text
        
        log_test("POST /gmail/watch returns 503 (no Pub/Sub topic)", success,
                f"Status: {resp.status_code}, Message: {message}")
        check_no_secrets(resp.text, "gmail/watch endpoint")
        
        return success
    except Exception as e:
        log_test("POST /gmail/watch returns 503 (no Pub/Sub topic)", False, str(e))
        return False

def test_gmail_push_webhook():
    """Test 4.4: POST /api/gmail/push (public webhook) with empty/invalid body"""
    try:
        # Test with empty body
        resp = requests.post(f"{BASE_URL}/gmail/push", json={}, timeout=10)
        data = resp.json()
        
        ok = data.get("ok")
        
        success = resp.status_code == 200 and ok == True
        
        log_test("POST /gmail/push webhook returns 200 {ok:true} for empty body", success,
                f"Status: {resp.status_code}, ok: {ok}")
        check_no_secrets(data, "gmail/push endpoint")
        
        return success
    except Exception as e:
        log_test("POST /gmail/push webhook returns 200 {ok:true} for empty body", False, str(e))
        return False

def test_email_compose_sent(token: str):
    """Test 5.1: POST /api/emails/compose (sent email with cc/bcc/attachments)"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "to": "recipient@example.com",
            "subject": "Test Email with Cc/Bcc",
            "body": "This is a test email body.",
            "cc": "cc@example.com",
            "bcc": "bcc@example.com",
            "attachments": [],
            "draft": False
        }
        
        resp = requests.post(f"{BASE_URL}/emails/compose", json=payload, headers=headers, timeout=10)
        data = resp.json()
        
        folder = data.get("folder")
        has_cc = data.get("cc") == "cc@example.com"
        has_bcc = data.get("bcc") == "bcc@example.com"
        
        success = resp.status_code == 200 and folder == "sent" and has_cc and has_bcc
        
        log_test("POST /emails/compose (sent) returns folder='sent' with cc/bcc", success,
                f"Status: {resp.status_code}, folder: {folder}, cc: {data.get('cc')}, bcc: {data.get('bcc')}")
        check_no_secrets(data, "emails/compose endpoint")
        
        return data.get("threadId") if success else None
    except Exception as e:
        log_test("POST /emails/compose (sent) returns folder='sent' with cc/bcc", False, str(e))
        return None

def test_email_compose_draft(token: str):
    """Test 5.2: POST /api/emails/compose (draft)"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "to": "draft@example.com",
            "subject": "Test Draft Email",
            "body": "This is a draft email.",
            "cc": "",
            "bcc": "",
            "attachments": [],
            "draft": True
        }
        
        resp = requests.post(f"{BASE_URL}/emails/compose", json=payload, headers=headers, timeout=10)
        data = resp.json()
        
        folder = data.get("folder")
        
        success = resp.status_code == 200 and folder == "drafts"
        
        log_test("POST /emails/compose (draft) returns folder='drafts'", success,
                f"Status: {resp.status_code}, folder: {folder}")
        check_no_secrets(data, "emails/compose draft endpoint")
        
        return data.get("threadId") if success else None
    except Exception as e:
        log_test("POST /emails/compose (draft) returns folder='drafts'", False, str(e))
        return None

def test_email_list_drafts(token: str):
    """Test 5.3: GET /api/emails?folder=drafts"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(f"{BASE_URL}/emails", params={"folder": "drafts"}, 
                           headers=headers, timeout=10)
        data = resp.json()
        
        is_array = isinstance(data, list)
        
        success = resp.status_code == 200 and is_array
        
        log_test("GET /emails?folder=drafts returns array", success,
                f"Status: {resp.status_code}, is_array: {is_array}, count: {len(data) if is_array else 0}")
        check_no_secrets(data, "emails list drafts endpoint")
        
        return success
    except Exception as e:
        log_test("GET /emails?folder=drafts returns array", False, str(e))
        return False

def test_email_list_inbox(token: str):
    """Test 5.4: GET /api/emails?folder=inbox"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(f"{BASE_URL}/emails", params={"folder": "inbox"}, 
                           headers=headers, timeout=10)
        data = resp.json()
        
        is_array = isinstance(data, list)
        
        success = resp.status_code == 200 and is_array
        
        log_test("GET /emails?folder=inbox returns array", success,
                f"Status: {resp.status_code}, is_array: {is_array}, count: {len(data) if is_array else 0}")
        check_no_secrets(data, "emails list inbox endpoint")
        
        # Return first thread ID for further testing
        return data[0].get("threadId") if is_array and len(data) > 0 else None
    except Exception as e:
        log_test("GET /emails?folder=inbox returns array", False, str(e))
        return None

def test_thread_read(token: str, thread_id: str):
    """Test 5.5: GET /api/threads/{threadId}"""
    if not thread_id:
        log_test("GET /threads/{threadId} works", False, "No thread ID available")
        return False
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(f"{BASE_URL}/threads/{thread_id}", headers=headers, timeout=10)
        data = resp.json()
        
        has_thread_id = "threadId" in data
        has_messages = "messages" in data
        
        success = resp.status_code == 200 and has_thread_id and has_messages
        
        log_test("GET /threads/{threadId} works", success,
                f"Status: {resp.status_code}, has_threadId: {has_thread_id}, has_messages: {has_messages}")
        check_no_secrets(data, "threads read endpoint")
        
        return success
    except Exception as e:
        log_test("GET /threads/{threadId} works", False, str(e))
        return False

def test_email_patch(token: str, thread_id: str):
    """Test 5.6: PATCH /api/emails/{threadId} (star and important)"""
    if not thread_id:
        log_test("PATCH /emails/{threadId} updates star/important", False, "No thread ID available")
        return False
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test star
        payload = {"star": True}
        resp = requests.patch(f"{BASE_URL}/emails/{thread_id}", json=payload, 
                             headers=headers, timeout=10)
        data = resp.json()
        
        star_ok = resp.status_code == 200 and data.get("ok") == True
        
        # Test important
        payload = {"important": True}
        resp = requests.patch(f"{BASE_URL}/emails/{thread_id}", json=payload, 
                             headers=headers, timeout=10)
        data = resp.json()
        
        important_ok = resp.status_code == 200 and data.get("ok") == True
        
        success = star_ok and important_ok
        
        log_test("PATCH /emails/{threadId} updates star/important", success,
                f"star_ok: {star_ok}, important_ok: {important_ok}")
        check_no_secrets(data, "emails patch endpoint")
        
        return success
    except Exception as e:
        log_test("PATCH /emails/{threadId} updates star/important", False, str(e))
        return False

def test_email_delete(token: str, thread_id: str):
    """Test 5.7: DELETE /api/emails/{threadId} (trash then permanent)"""
    if not thread_id:
        log_test("DELETE /emails/{threadId} moves to trash then deletes", False, "No thread ID available")
        return False
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        
        # First delete - should move to trash
        resp = requests.delete(f"{BASE_URL}/emails/{thread_id}", headers=headers, timeout=10)
        data = resp.json()
        
        first_ok = resp.status_code == 200 and data.get("ok") == True
        
        # Second delete - should permanently delete
        resp = requests.delete(f"{BASE_URL}/emails/{thread_id}", headers=headers, timeout=10)
        data = resp.json()
        
        second_ok = resp.status_code == 200 and data.get("ok") == True
        
        # Verify not in trash list
        resp = requests.get(f"{BASE_URL}/emails", params={"folder": "trash"}, 
                           headers=headers, timeout=10)
        trash_list = resp.json()
        
        not_in_trash = not any(email.get("threadId") == thread_id for email in trash_list)
        
        success = first_ok and second_ok and not_in_trash
        
        log_test("DELETE /emails/{threadId} moves to trash then deletes permanently", success,
                f"first_delete_ok: {first_ok}, second_delete_ok: {second_ok}, not_in_trash: {not_in_trash}")
        check_no_secrets(data, "emails delete endpoint")
        
        return success
    except Exception as e:
        log_test("DELETE /emails/{threadId} moves to trash then deletes permanently", False, str(e))
        return False

def test_ai_compose(token: str):
    """Test 6.1: POST /api/ai/compose"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "instruction": "Write an email asking for a meeting next week",
            "tone": "Professional"
        }
        
        resp = requests.post(f"{BASE_URL}/ai/compose", json=payload, headers=headers, timeout=30)
        data = resp.json()
        
        has_subject = "subject" in data
        has_body = "body" in data
        
        success = resp.status_code == 200 and has_subject and has_body
        
        log_test("POST /ai/compose returns {subject, body}", success,
                f"Status: {resp.status_code}, has_subject: {has_subject}, has_body: {has_body}")
        check_no_secrets(data, "ai/compose endpoint")
        
        return success
    except Exception as e:
        log_test("POST /ai/compose returns {subject, body}", False, str(e))
        return False

def test_ai_reply(token: str, thread_id: str):
    """Test 6.2: POST /api/ai/reply"""
    if not thread_id:
        log_test("POST /ai/reply returns {text}", False, "No thread ID available")
        return False
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "threadId": thread_id,
            "tone": "Professional",
            "action": "reply"
        }
        
        resp = requests.post(f"{BASE_URL}/ai/reply", json=payload, headers=headers, timeout=30)
        data = resp.json()
        
        has_text = "text" in data
        
        success = resp.status_code == 200 and has_text
        
        log_test("POST /ai/reply returns {text}", success,
                f"Status: {resp.status_code}, has_text: {has_text}")
        check_no_secrets(data, "ai/reply endpoint")
        
        return success
    except Exception as e:
        log_test("POST /ai/reply returns {text}", False, str(e))
        return False

def test_ai_understand(token: str, thread_id: str):
    """Test 6.3: POST /api/ai/understand/{tid}"""
    if not thread_id:
        log_test("POST /ai/understand/{tid} returns intent/topic", False, "No thread ID available")
        return False
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.post(f"{BASE_URL}/ai/understand/{thread_id}", headers=headers, timeout=30)
        data = resp.json()
        
        has_intent = "intent" in data
        has_topic = "topic" in data
        
        success = resp.status_code == 200 and has_intent and has_topic
        
        log_test("POST /ai/understand/{tid} returns intent/topic", success,
                f"Status: {resp.status_code}, has_intent: {has_intent}, has_topic: {has_topic}")
        check_no_secrets(data, "ai/understand endpoint")
        
        return success
    except Exception as e:
        log_test("POST /ai/understand/{tid} returns intent/topic", False, str(e))
        return False

def test_ai_thread_summary(token: str, thread_id: str):
    """Test 6.4: POST /api/ai/thread/{tid}"""
    if not thread_id:
        log_test("POST /ai/thread/{tid} returns summary", False, "No thread ID available")
        return False
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.post(f"{BASE_URL}/ai/thread/{thread_id}", headers=headers, timeout=30)
        data = resp.json()
        
        has_summary = "summary" in data
        
        success = resp.status_code == 200 and has_summary
        
        log_test("POST /ai/thread/{tid} returns summary", success,
                f"Status: {resp.status_code}, has_summary: {has_summary}")
        check_no_secrets(data, "ai/thread endpoint")
        
        return success
    except Exception as e:
        log_test("POST /ai/thread/{tid} returns summary", False, str(e))
        return False

def test_ai_ask(token: str):
    """Test 6.5: POST /api/ai/ask"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "question": "What emails do I need to respond to?"
        }
        
        resp = requests.post(f"{BASE_URL}/ai/ask", json=payload, headers=headers, timeout=30)
        data = resp.json()
        
        has_answer = "answer" in data
        
        success = resp.status_code == 200 and has_answer
        
        log_test("POST /ai/ask returns {answer}", success,
                f"Status: {resp.status_code}, has_answer: {has_answer}")
        check_no_secrets(data, "ai/ask endpoint")
        
        return success
    except Exception as e:
        log_test("POST /ai/ask returns {answer}", False, str(e))
        return False

def test_ai_email_to_task(token: str, thread_id: str):
    """Test 6.6: POST /api/ai/email-to-task/{tid}"""
    if not thread_id:
        log_test("POST /ai/email-to-task/{tid} returns task with title", False, "No thread ID available")
        return False
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.post(f"{BASE_URL}/ai/email-to-task/{thread_id}", headers=headers, timeout=30)
        data = resp.json()
        
        has_title = "title" in data
        
        success = resp.status_code == 200 and has_title
        
        log_test("POST /ai/email-to-task/{tid} returns task with title", success,
                f"Status: {resp.status_code}, has_title: {has_title}")
        check_no_secrets(data, "ai/email-to-task endpoint")
        
        return success
    except Exception as e:
        log_test("POST /ai/email-to-task/{tid} returns task with title", False, str(e))
        return False

def test_push_register_short_token(token: str):
    """Test 7.1: POST /api/push/register with short token (<20 chars)"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "token": "short",
            "platform": "android"
        }
        
        resp = requests.post(f"{BASE_URL}/push/register", json=payload, headers=headers, timeout=10)
        
        success = resp.status_code == 422
        
        log_test("POST /push/register with short token returns 422", success,
                f"Status: {resp.status_code}")
        check_no_secrets(resp.text, "push/register short token endpoint")
        
        return success
    except Exception as e:
        log_test("POST /push/register with short token returns 422", False, str(e))
        return False

def test_push_register_valid_token(token: str):
    """Test 7.2: POST /api/push/register with valid long token"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "token": "a" * 50,  # Valid long token
            "platform": "android"
        }
        
        resp = requests.post(f"{BASE_URL}/push/register", json=payload, headers=headers, timeout=10)
        data = resp.json()
        
        registered = data.get("registered")
        
        success = resp.status_code == 200 and registered == True
        
        log_test("POST /push/register with valid token returns {registered:true}", success,
                f"Status: {resp.status_code}, registered: {registered}")
        check_no_secrets(data, "push/register valid token endpoint")
        
        return success
    except Exception as e:
        log_test("POST /push/register with valid token returns {registered:true}", False, str(e))
        return False

def main():
    print("=" * 80)
    print("FMAIL GMAIL CLIENT BACKEND TEST SUITE")
    print("=" * 80)
    print()
    
    # Test 1: Root endpoint
    print("### 1. ROOT ENDPOINT ###")
    test_root()
    print()
    
    # Test 2: Auth identity removal
    print("### 2. AUTH IDENTITY REMOVAL ###")
    test_check_handle_removed()
    test_signup_no_username()
    demo_token = test_demo_login()
    if demo_token:
        test_auth_me(demo_token)
    print()
    
    # Test 3: Google OAuth endpoints
    print("### 3. GOOGLE OAUTH ENDPOINTS ###")
    test_google_config()
    test_google_login_url()
    test_google_exchange_invalid()
    if demo_token:
        test_google_authorize(demo_token)
        test_google_disconnect(demo_token)
    print()
    
    # Test 4: Gmail endpoints
    print("### 4. GMAIL ENDPOINTS (demo has no Gmail) ###")
    if demo_token:
        test_gmail_status(demo_token)
        test_gmail_sync(demo_token)
        test_gmail_watch(demo_token)
    test_gmail_push_webhook()
    print()
    
    # Test 5: Email local fallback
    print("### 5. EMAIL LOCAL FALLBACK (demo account) ###")
    if demo_token:
        sent_thread_id = test_email_compose_sent(demo_token)
        draft_thread_id = test_email_compose_draft(demo_token)
        test_email_list_drafts(demo_token)
        inbox_thread_id = test_email_list_inbox(demo_token)
        
        # Use inbox thread for further tests
        test_thread_id = inbox_thread_id or sent_thread_id
        
        test_thread_read(demo_token, test_thread_id)
        test_email_patch(demo_token, test_thread_id)
        
        # Use draft thread for delete test (don't delete inbox emails)
        test_email_delete(demo_token, draft_thread_id)
    print()
    
    # Test 6: AI endpoints
    print("### 6. AI ENDPOINTS (cached emails) ###")
    if demo_token:
        test_ai_compose(demo_token)
        # Use inbox thread for AI tests
        ai_thread_id = inbox_thread_id or sent_thread_id
        test_ai_reply(demo_token, ai_thread_id)
        test_ai_understand(demo_token, ai_thread_id)
        test_ai_thread_summary(demo_token, ai_thread_id)
        test_ai_ask(demo_token)
        test_ai_email_to_task(demo_token, ai_thread_id)
    print()
    
    # Test 7: Push notifications
    print("### 7. PUSH NOTIFICATIONS ###")
    if demo_token:
        test_push_register_short_token(demo_token)
        test_push_register_valid_token(demo_token)
    print()
    
    # Summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"✅ PASSED: {passed}")
    print(f"❌ FAILED: {failed}")
    print(f"📊 TOTAL:  {passed + failed}")
    print()
    
    if failures:
        print("FAILED TESTS:")
        for failure in failures:
            print(f"  - {failure}")
        print()
    
    if failed == 0:
        print("🎉 ALL TESTS PASSED!")
    else:
        print(f"⚠️  {failed} test(s) failed. See details above.")
    
    print("=" * 80)

if __name__ == "__main__":
    main()
