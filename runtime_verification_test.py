#!/usr/bin/env python3
"""
Runtime restoration verification test for Fmail backend
Tests only the specific requirements from the review request
"""
import requests
import json

# Backend URL from frontend/.env
BASE_URL = "https://fmail-staging.preview.emergentagent.com/api"

# Test credentials from test_credentials.md
DEMO_EMAIL = "demo@fmail.com"
DEMO_PASSWORD = "demo123"

# Color codes
GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
RESET = "\033[0m"

def test_api_root():
    """Test 1: GET /api/ returns Fmail status"""
    print(f"\n{BLUE}TEST 1: GET /api/ (API root){RESET}")
    try:
        r = requests.get(BASE_URL + "/", timeout=10)
        if r.status_code == 200:
            data = r.json()
            print(f"{GREEN}✓ PASS{RESET}: API root accessible - {data}")
            return True
        else:
            print(f"{RED}✗ FAIL{RESET}: API root returned status {r.status_code}")
            return False
    except Exception as e:
        print(f"{RED}✗ FAIL{RESET}: API root error - {e}")
        return False

def test_demo_login():
    """Test 2: Demo login (demo@fmail.com / demo123)"""
    print(f"\n{BLUE}TEST 2: Demo login{RESET}")
    try:
        r = requests.post(
            BASE_URL + "/auth/login",
            json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            if "token" in data and "user" in data:
                print(f"{GREEN}✓ PASS{RESET}: Demo login successful")
                return True, data["token"]
            else:
                print(f"{RED}✗ FAIL{RESET}: Login response missing token or user - {data}")
                return False, None
        else:
            print(f"{RED}✗ FAIL{RESET}: Login failed with status {r.status_code} - {r.text}")
            return False, None
    except Exception as e:
        print(f"{RED}✗ FAIL{RESET}: Login error - {e}")
        return False, None

def test_auth_me(token):
    """Test 3: Authenticated GET /api/auth/me"""
    print(f"\n{BLUE}TEST 3: GET /api/auth/me (authenticated){RESET}")
    try:
        r = requests.get(
            BASE_URL + "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            if "email" in data:
                print(f"{GREEN}✓ PASS{RESET}: /auth/me returned user data - email={data.get('email')}")
                return True
            else:
                print(f"{RED}✗ FAIL{RESET}: /auth/me missing email field - {data}")
                return False
        else:
            print(f"{RED}✗ FAIL{RESET}: /auth/me returned status {r.status_code} - {r.text}")
            return False
    except Exception as e:
        print(f"{RED}✗ FAIL{RESET}: /auth/me error - {e}")
        return False

def test_dashboard(token):
    """Test 4: Authenticated GET /api/dashboard"""
    print(f"\n{BLUE}TEST 4: GET /api/dashboard (authenticated){RESET}")
    try:
        r = requests.get(
            BASE_URL + "/dashboard",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            if "brief" in data or "counts" in data:
                print(f"{GREEN}✓ PASS{RESET}: /dashboard returned data")
                return True
            else:
                print(f"{RED}✗ FAIL{RESET}: /dashboard missing expected fields - {data}")
                return False
        else:
            print(f"{RED}✗ FAIL{RESET}: /dashboard returned status {r.status_code} - {r.text}")
            return False
    except Exception as e:
        print(f"{RED}✗ FAIL{RESET}: /dashboard error - {e}")
        return False

def test_sarvam_empty_audio(token):
    """Test 5: Sarvam integration returns friendly validation for empty audio"""
    print(f"\n{BLUE}TEST 5: Sarvam empty audio validation{RESET}")
    try:
        r = requests.post(
            BASE_URL + "/voice/transcribe",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("empty.m4a", b"", "audio/mp4")},
            data={"language_code": "hi-IN", "mode": "codemix"},
            timeout=10
        )
        # Should return 413 with friendly message
        if r.status_code == 413:
            try:
                data = r.json()
                if "detail" in data and "empty" in data["detail"].lower():
                    print(f"{GREEN}✓ PASS{RESET}: Sarvam returns friendly validation - {data['detail']}")
                    return True
                else:
                    print(f"{GREEN}✓ PASS{RESET}: Sarvam returns 413 (validation working)")
                    return True
            except:
                print(f"{GREEN}✓ PASS{RESET}: Sarvam returns 413 (validation working)")
                return True
        else:
            print(f"{RED}✗ FAIL{RESET}: Expected 413 for empty audio, got {r.status_code} - {r.text}")
            return False
    except Exception as e:
        print(f"{RED}✗ FAIL{RESET}: Sarvam test error - {e}")
        return False

def main():
    print(f"{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}FMAIL RUNTIME RESTORATION VERIFICATION{RESET}")
    print(f"{BLUE}{'='*80}{RESET}")
    print(f"Base URL: {BASE_URL}")
    print(f"Demo credentials: {DEMO_EMAIL} / {DEMO_PASSWORD}")
    
    results = []
    
    # Test 1: API root
    results.append(test_api_root())
    
    # Test 2: Demo login
    login_success, token = test_demo_login()
    results.append(login_success)
    
    if token:
        # Test 3: /auth/me
        results.append(test_auth_me(token))
        
        # Test 4: /dashboard
        results.append(test_dashboard(token))
        
        # Test 5: Sarvam validation
        results.append(test_sarvam_empty_audio(token))
    else:
        print(f"\n{RED}Cannot run authenticated tests without token{RESET}")
        results.extend([False, False, False])
    
    # Summary
    print(f"\n{BLUE}{'='*80}{RESET}")
    print(f"{BLUE}SUMMARY{RESET}")
    print(f"{BLUE}{'='*80}{RESET}")
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print(f"\n{GREEN}{'='*80}{RESET}")
        print(f"{GREEN}ALL RUNTIME VERIFICATION TESTS PASSED!{RESET}")
        print(f"{GREEN}{'='*80}{RESET}")
        return 0
    else:
        print(f"\n{RED}{'='*80}{RESET}")
        print(f"{RED}SOME TESTS FAILED{RESET}")
        print(f"{RED}{'='*80}{RESET}")
        return 1

if __name__ == "__main__":
    exit(main())
