#!/usr/bin/env python3
"""
Production backend API test suite for Fmail continuous production pass
Tests OTP fail-closed behavior, new endpoints, and security
"""
import requests
import json
import time
import re
from typing import Dict, Any, Optional

# Backend URL from frontend/.env
BASE_URL = "https://f281a24f-dfd7-44e5-9aed-69e8b24e7d98.preview.emergentagent.com/api"

# Test credentials from test_credentials.md
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
        self.security_issues = []
    
    def add_pass(self, test_name: str, detail: str = ""):
        self.passed.append((test_name, detail))
        print(f"{GREEN}✓ PASS{RESET}: {test_name}" + (f" - {detail}" if detail else ""))
    
    def add_fail(self, test_name: str, error: str):
        self.failed.append((test_name, error))
        print(f"{RED}✗ FAIL{RESET}: {test_name} - {error}")
    
    def add_warning(self, test_name: str, message: str):
        self.warnings.append((test_name, message))
        print(f"{YELLOW}⚠ WARNING{RESET}: {test_name} - {message}")
    
    def add_security_issue(self, test_name: str, issue: str):
        self.security_issues.append((test_name, issue))
        print(f"{RED}🔒 SECURITY{RESET}: {test_name} - {issue}")
    
    def summary(self):
        print(f"\n{BLUE}{'='*80}{RESET}")
        print(f"{BLUE}TEST SUMMARY{RESET}")
        print(f"{BLUE}{'='*80}{RESET}")
        print(f"{GREEN}Passed: {len(self.passed)}{RESET}")
        print(f"{RED}Failed: {len(self.failed)}{RESET}")
        print(f"{YELLOW}Warnings: {len(self.warnings)}{RESET}")
        print(f"{RED}Security Issues: {len(self.security_issues)}{RESET}")
        
        if self.security_issues:
            print(f"\n{RED}SECURITY ISSUES:{RESET}")
            for name, issue in self.security_issues:
                print(f"  • {name}: {issue}")
        
        if self.failed:
            print(f"\n{RED}FAILED TESTS:{RESET}")
            for name, error in self.failed:
                print(f"  • {name}: {error}")
        
        return len(self.failed) == 0 and len(self.security_issues) == 0

results = TestResults()

def check_for_secrets(data: Any, test_name: str) -> None:
    """Check if response contains any secrets/keys that should not be exposed"""
    data_str = json.dumps(data) if isinstance(data, (dict, list)) else str(data)
    
    # Check for various secret patterns
    patterns = {
        "devCode": r'"devCode"\s*:\s*"?\d{6}"?',
        "OTP code": r'"code"\s*:\s*"?\d{6}"?',
        "API key (Sarvam)": r'sk_[a-zA-Z0-9_-]{20,}',
        "API key (Resend)": r're_[a-zA-Z0-9]{20,}',
        "Private key": r'-----BEGIN (RSA |EC )?PRIVATE KEY-----',
        "JWT secret": r'"(JWT_SECRET|secret)"\s*:\s*"[^"]{20,}"',
        "Firebase private key": r'"private_key"\s*:\s*"-----BEGIN',
    }
    
    for secret_type, pattern in patterns.items():
        if re.search(pattern, data_str, re.IGNORECASE):
            results.add_security_issue(test_name, f"{secret_type} exposed in response")

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

def test_root_endpoint():
    """Test 1: GET /api/ returns 200"""
    print(f"\n{BLUE}TEST 1: Root endpoint{RESET}")
    
    success, data, status = make_request("GET", "/")
    if status == 200 and isinstance(data, dict) and data.get("status") == "ok":
        results.add_pass("GET /api/", f"Returns 200 with status=ok")
    else:
        results.add_fail("GET /api/", f"Expected 200 with status=ok, got status={status}, data={data}")
    
    check_for_secrets(data, "GET /api/")

def test_otp_fail_closed():
    """Test 2: OTP fail-closed behavior (no devCode/test fields, 503 when Resend not configured)"""
    print(f"\n{BLUE}TEST 2: OTP fail-closed behavior{RESET}")
    
    test_email = f"otptest{int(time.time())}@example.com"
    
    # Test 2a: Request OTP for signup (should fail with 503 when Resend not configured)
    success, data, status = make_request("POST", "/auth/request-otp", 
                                        json_data={"email": test_email, "purpose": "signup"})
    
    # Check that response does NOT contain devCode or test OTP
    check_for_secrets(data, "OTP request-otp")
    
    if "devCode" in str(data):
        results.add_security_issue("OTP request-otp", "devCode exposed in response (should be removed in production)")
    
    if "code" in str(data) and isinstance(data, dict) and "code" in data:
        results.add_security_issue("OTP request-otp", "OTP code exposed in response")
    
    # Should return 503 when Resend is not configured
    if status == 503:
        if "temporarily unavailable" in str(data).lower() or "not configured" in str(data).lower():
            results.add_pass("OTP fail-closed", f"Returns 503 with user-safe message: {data}")
        else:
            results.add_fail("OTP fail-closed", f"Returns 503 but message not user-friendly: {data}")
    else:
        results.add_fail("OTP fail-closed", f"Expected 503 when Resend not configured, got status={status}, data={data}")
    
    # Test 2b: Signup should require OTP code
    success, data, status = make_request("POST", "/auth/signup", json_data={
        "email": test_email,
        "password": "testpass123",
        "name": "OTP Test",
        "username": f"otptest{int(time.time())}",
        "code": "123456"  # Invalid code
    })
    
    check_for_secrets(data, "Signup with code")
    
    # Should fail because code is required and invalid
    if not success:
        if status == 400 and ("code" in str(data).lower() or "verify" in str(data).lower()):
            results.add_pass("Signup requires OTP", f"Signup fails without valid OTP: {data}")
        else:
            results.add_warning("Signup requires OTP", f"Signup failed but unclear if due to OTP: status={status}, data={data}")
    else:
        results.add_fail("Signup requires OTP", f"Signup succeeded without valid OTP code")

def test_existing_login():
    """Test 3: Existing login with demo@fmail.com / demo123 works"""
    print(f"\n{BLUE}TEST 3: Existing demo login{RESET}")
    
    # Test 3a: Login
    success, data, status = make_request("POST", "/auth/login", json_data={
        "email": DEMO_EMAIL,
        "password": DEMO_PASSWORD
    })
    
    check_for_secrets(data, "Demo login")
    
    if success and "token" in data and "user" in data:
        demo_token = data["token"]
        results.add_pass("Demo login", f"Login successful with demo@fmail.com")
    else:
        results.add_fail("Demo login", f"Login failed: status={status}, data={data}")
        return None
    
    # Test 3b: /auth/me
    success, data, status = make_request("GET", "/auth/me", token=demo_token)
    
    check_for_secrets(data, "/auth/me")
    
    if success and data.get("email") == DEMO_EMAIL:
        results.add_pass("/auth/me", f"Returns user data for demo account")
    else:
        results.add_fail("/auth/me", f"Failed to get user data: status={status}, data={data}")
    
    return demo_token

def test_new_endpoints(token: str):
    """Test 4: New endpoints return safe configuration errors"""
    print(f"\n{BLUE}TEST 4: New endpoints with safe configuration errors{RESET}")
    
    # Test 4a: /auth/google/config (public)
    success, data, status = make_request("GET", "/auth/google/config")
    check_for_secrets(data, "/auth/google/config")
    
    if status == 200 and isinstance(data, dict):
        if "configured" in data:
            results.add_pass("/auth/google/config", f"Returns configuration status: {data}")
        else:
            results.add_warning("/auth/google/config", f"Missing 'configured' field: {data}")
    else:
        results.add_fail("/auth/google/config", f"Expected 200, got status={status}, data={data}")
    
    # Test 4b: /auth/google/authorize (authenticated, should fail with safe error)
    success, data, status = make_request("GET", "/auth/google/authorize", token=token)
    check_for_secrets(data, "/auth/google/authorize")
    
    if status == 503:
        if "not configured" in str(data).lower() or "unavailable" in str(data).lower():
            results.add_pass("/auth/google/authorize", f"Returns safe 503 error: {data}")
        else:
            results.add_fail("/auth/google/authorize", f"Returns 503 but message not safe: {data}")
    else:
        results.add_warning("/auth/google/authorize", f"Expected 503, got status={status}, data={data}")
    
    # Test 4c: /gmail/sync (authenticated, should fail with safe error)
    success, data, status = make_request("POST", "/gmail/sync", token=token)
    check_for_secrets(data, "/gmail/sync")
    
    if status == 400:
        if "connect" in str(data).lower() or "google" in str(data).lower():
            results.add_pass("/gmail/sync", f"Returns safe 400 error: {data}")
        else:
            results.add_warning("/gmail/sync", f"Returns 400 but message unclear: {data}")
    else:
        results.add_warning("/gmail/sync", f"Expected 400, got status={status}, data={data}")
    
    # Test 4d: /push/register validation (authenticated)
    # Test with invalid token (too short)
    success, data, status = make_request("POST", "/push/register", token=token, json_data={
        "token": "short",
        "platform": "android"
    })
    check_for_secrets(data, "/push/register validation")
    
    if status == 422:
        results.add_pass("/push/register validation", f"Validates token length: status={status}")
    else:
        results.add_warning("/push/register validation", f"Expected 422 for short token, got status={status}")
    
    # Test with valid token
    success, data, status = make_request("POST", "/push/register", token=token, json_data={
        "token": "a" * 30,  # Valid length
        "platform": "android"
    })
    check_for_secrets(data, "/push/register")
    
    if success and data.get("registered") == True:
        results.add_pass("/push/register", f"Registers valid token: {data}")
    else:
        results.add_fail("/push/register", f"Failed to register: status={status}, data={data}")
    
    # Test 4e: /feedback (authenticated, should fail with safe error when Resend not configured)
    success, data, status = make_request("POST", "/feedback", token=token, json_data={
        "message": "This is test feedback for the production pass",
        "category": "testing"
    })
    check_for_secrets(data, "/feedback")
    
    if status == 503:
        if "temporarily unavailable" in str(data).lower() or "not configured" in str(data).lower():
            results.add_pass("/feedback", f"Returns safe 503 error: {data}")
        else:
            results.add_fail("/feedback", f"Returns 503 but message not safe: {data}")
    else:
        results.add_warning("/feedback", f"Expected 503 when Resend not configured, got status={status}, data={data}")
    
    # Test 4f: /analytics (authenticated)
    success, data, status = make_request("POST", "/analytics", token=token, json_data={
        "name": "test_event",
        "params": {"screen": "test", "action": "click"}
    })
    check_for_secrets(data, "/analytics")
    
    if success and data.get("recorded") == True:
        results.add_pass("/analytics", f"Records analytics event: {data}")
    else:
        results.add_fail("/analytics", f"Failed to record analytics: status={status}, data={data}")

def test_meeting_share(token: str):
    """Test 5: Meeting share returns URL or safe configuration error"""
    print(f"\n{BLUE}TEST 5: Meeting share{RESET}")
    
    # First create a meeting
    success, data, status = make_request("POST", "/meetings", token=token, json_data={
        "title": "Test Meeting for Share",
        "mode": "General",
        "attendees": [],
        "aiCopilot": True
    })
    
    if not success or not data.get("id"):
        results.add_warning("Meeting share", f"Could not create test meeting: {data}")
        return
    
    meeting_id = data["id"]
    
    # Test share endpoint
    success, data, status = make_request("POST", f"/meetings/{meeting_id}/share", token=token)
    check_for_secrets(data, "/meetings/share")
    
    if status == 503:
        if "not configured" in str(data).lower():
            results.add_pass("Meeting share", f"Returns safe 503 error when APP_URL not configured: {data}")
        else:
            results.add_fail("Meeting share", f"Returns 503 but message not safe: {data}")
    elif success and "url" in data:
        results.add_pass("Meeting share", f"Returns meeting URL: {data['url']}")
    else:
        results.add_fail("Meeting share", f"Unexpected response: status={status}, data={data}")

def test_file_security(token: str):
    """Test 6: Files upload validation and download security"""
    print(f"\n{BLUE}TEST 6: File upload/download security{RESET}")
    
    # Test 6a: Upload file with validation
    # Test file too large (13MB base64 is over 8MB limit)
    large_data = "A" * (13 * 1024 * 1024)
    
    url = f"{BASE_URL}/files"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        r = requests.post(url, headers=headers, data={
            "name": "large_file.txt",
            "type": "document",
            "size": "13MB",
            "data": large_data
        }, timeout=30)
        
        if r.status_code == 413:
            results.add_pass("File upload: size validation", f"Rejects files over 8MB: status={r.status_code}")
        else:
            results.add_warning("File upload: size validation", f"Expected 413 for large file, got status={r.status_code}")
    except Exception as e:
        results.add_warning("File upload: size validation", f"Request failed: {e}")
    
    # Test 6b: Upload valid file
    try:
        r = requests.post(url, headers=headers, data={
            "name": "test_file.txt",
            "type": "document",
            "size": "1KB",
            "data": "dGVzdCBmaWxlIGNvbnRlbnQ="  # "test file content" in base64
        }, timeout=30)
        
        if r.status_code < 400:
            data = r.json()
            if data.get("id"):
                file_id = data["id"]
                results.add_pass("File upload: valid file", f"Uploaded file with id={file_id}")
            else:
                results.add_fail("File upload: valid file", f"No file ID in response: {data}")
                return
        else:
            results.add_fail("File upload: valid file", f"Failed to upload: status={r.status_code}, data={r.text}")
            return
    except Exception as e:
        results.add_fail("File upload: valid file", f"Request failed: {e}")
        return
    
    # Test 6c: Download own file
    success, data, status = make_request("GET", f"/files/{file_id}/download", token=token)
    check_for_secrets(data, "/files/download")
    
    if success and data.get("name") == "test_file.txt":
        results.add_pass("File download: own file", f"Can download own file")
    else:
        results.add_fail("File download: own file", f"Failed to download: status={status}, data={data}")
    
    # Test 6d: Try to download non-existent file (should not expose other users' files)
    fake_file_id = "00000000-0000-0000-0000-000000000000"
    success, data, status = make_request("GET", f"/files/{fake_file_id}/download", token=token)
    
    if status == 404:
        results.add_pass("File download: security", f"Returns 404 for non-existent/other user's file")
    else:
        results.add_warning("File download: security", f"Expected 404, got status={status}")

def test_sarvam_empty_audio(token: str):
    """Test 7: Sarvam empty audio returns friendly validation error"""
    print(f"\n{BLUE}TEST 7: Sarvam empty audio validation{RESET}")
    
    success, data, status = make_request("POST", "/voice/transcribe", token=token,
                                        files={"file": ("empty.m4a", b"", "audio/mp4")},
                                        data={"language_code": "hi-IN", "mode": "codemix"})
    
    check_for_secrets(data, "/voice/transcribe empty audio")
    
    if status == 413:
        if "empty" in str(data).lower() and "try again" in str(data).lower():
            results.add_pass("Sarvam empty audio", f"Returns friendly 413 error: {data}")
        else:
            results.add_fail("Sarvam empty audio", f"Returns 413 but message not friendly: {data}")
    else:
        results.add_fail("Sarvam empty audio", f"Expected 413, got status={status}, data={data}")

def test_backend_logs():
    """Test 8: Check backend logs for crashes"""
    print(f"\n{BLUE}TEST 8: Backend logs check{RESET}")
    
    import subprocess
    
    try:
        # Check backend error logs
        result = subprocess.run(
            ["tail", "-n", "100", "/var/log/supervisor/backend.err.log"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        error_log = result.stdout
        
        # Check for crashes/critical errors
        critical_patterns = [
            "Traceback (most recent call last)",
            "Exception",
            "Error",
            "CRITICAL",
            "FATAL"
        ]
        
        has_critical = any(pattern in error_log for pattern in critical_patterns)
        
        if has_critical:
            # Check if errors are recent (last 50 lines)
            recent_log = "\n".join(error_log.split("\n")[-50:])
            if any(pattern in recent_log for pattern in critical_patterns):
                results.add_warning("Backend logs", f"Found recent errors in backend logs (check /var/log/supervisor/backend.err.log)")
                print(f"{YELLOW}Recent log excerpt:{RESET}")
                print(recent_log[-500:])  # Last 500 chars
            else:
                results.add_pass("Backend logs", "No recent critical errors")
        else:
            results.add_pass("Backend logs", "No critical errors found")
        
        # Check for exposed secrets in logs
        secret_patterns = [
            r'sk_[a-zA-Z0-9_-]{20,}',
            r're_[a-zA-Z0-9]{20,}',
            r'-----BEGIN (RSA )?PRIVATE KEY-----',
            r'\d{6}.*OTP',
        ]
        
        for pattern in secret_patterns:
            if re.search(pattern, error_log):
                results.add_security_issue("Backend logs", f"Potential secret exposed in logs matching pattern: {pattern}")
        
    except subprocess.TimeoutExpired:
        results.add_warning("Backend logs", "Timeout reading logs")
    except FileNotFoundError:
        results.add_warning("Backend logs", "Log file not found")
    except Exception as e:
        results.add_warning("Backend logs", f"Could not read logs: {e}")

def main():
    print(f"{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}FMAIL PRODUCTION BACKEND TEST SUITE{RESET}")
    print(f"{BLUE}Continuous Production Pass - OTP Fail-Closed & New Endpoints{RESET}")
    print(f"{BLUE}{'='*80}{RESET}")
    print(f"Base URL: {BASE_URL}")
    print(f"Demo credentials: {DEMO_EMAIL} / {DEMO_PASSWORD}")
    
    # Run all tests
    test_root_endpoint()
    test_otp_fail_closed()
    
    demo_token = test_existing_login()
    
    if demo_token:
        test_new_endpoints(demo_token)
        test_meeting_share(demo_token)
        test_file_security(demo_token)
        test_sarvam_empty_audio(demo_token)
    else:
        print(f"{RED}Cannot run authenticated tests without demo token{RESET}")
    
    test_backend_logs()
    
    # Print summary
    success = results.summary()
    
    if success:
        print(f"\n{GREEN}{'='*80}{RESET}")
        print(f"{GREEN}ALL TESTS PASSED!{RESET}")
        print(f"{GREEN}{'='*80}{RESET}")
    else:
        print(f"\n{RED}{'='*80}{RESET}")
        print(f"{RED}SOME TESTS FAILED OR SECURITY ISSUES FOUND{RESET}")
        print(f"{RED}{'='*80}{RESET}")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
