import os, uuid, pytest, requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://run-mobile-app-6.preview.emergentagent.com").rstrip("/")

@pytest.fixture(scope="session")
def base_url():
    return BASE_URL

@pytest.fixture(scope="session")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s

@pytest.fixture(scope="session")
def signup_user(api):
    suffix = uuid.uuid4().hex[:8]
    email = f"TEST_{suffix}@fmail.dev"
    username = f"tuser{suffix}"
    body = {"email": email, "password": "secret123", "name": "Test User", "username": username}
    r = api.post(f"{BASE_URL}/api/auth/signup", json=body)
    assert r.status_code == 200, f"signup failed: {r.status_code} {r.text}"
    data = r.json()
    return {"token": data["token"], "user": data["user"], "email": email, "username": username, "password": "secret123"}

@pytest.fixture(scope="session")
def auth_headers(signup_user):
    return {"Authorization": f"Bearer {signup_user['token']}", "Content-Type": "application/json"}
