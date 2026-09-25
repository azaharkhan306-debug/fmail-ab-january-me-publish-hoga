"""End-to-end backend tests for Fmail API."""
import os, requests, pytest

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://fmail-ai-os.preview.emergentagent.com").rstrip("/")


# ------------------- health/auth -------------------
def test_root(api):
    r = api.get(f"{BASE_URL}/api/")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"


def test_signup_seeds_and_login(signup_user, api):
    # login separately
    r = api.post(f"{BASE_URL}/api/auth/login",
                 json={"email": signup_user["email"], "password": signup_user["password"]})
    assert r.status_code == 200
    d = r.json()
    assert "token" in d and d["user"]["email"] == signup_user["email"].lower()
    assert d["user"]["fmail"].endswith("@fmails.in")


def test_login_wrong_password(api, signup_user):
    r = api.post(f"{BASE_URL}/api/auth/login",
                 json={"email": signup_user["email"], "password": "wrong"})
    assert r.status_code == 401


def test_auth_me_and_profile_update(api, auth_headers):
    r = api.get(f"{BASE_URL}/api/auth/me", headers=auth_headers)
    assert r.status_code == 200
    assert "id" in r.json() and "password" not in r.json()

    r2 = api.put(f"{BASE_URL}/api/auth/profile",
                 headers=auth_headers,
                 json={"signature": "TEST_sig", "darkMode": "dark"})
    assert r2.status_code == 200
    assert r2.json()["signature"] == "TEST_sig"
    assert r2.json()["darkMode"] == "dark"


# ------------------- dashboard -------------------
def test_dashboard(api, auth_headers):
    r = api.get(f"{BASE_URL}/api/dashboard", headers=auth_headers)
    assert r.status_code == 200
    d = r.json()
    for k in ("brief", "unread", "needsAction", "waitingFor", "todayMeetings", "tasks", "counts"):
        assert k in d, f"missing {k}"
    assert isinstance(d["counts"], dict)


# ------------------- emails -------------------
def test_emails_inbox(api, auth_headers):
    r = api.get(f"{BASE_URL}/api/emails?folder=inbox", headers=auth_headers)
    assert r.status_code == 200
    lst = r.json()
    assert isinstance(lst, list) and len(lst) >= 5


def test_emails_filters(api, auth_headers):
    r = api.get(f"{BASE_URL}/api/emails?folder=inbox&filter=unread&account=gmail", headers=auth_headers)
    assert r.status_code == 200


def test_emails_starred(api, auth_headers):
    r = api.get(f"{BASE_URL}/api/emails?folder=starred", headers=auth_headers)
    assert r.status_code == 200


def test_thread_and_patch(api, auth_headers):
    r = api.get(f"{BASE_URL}/api/emails?folder=inbox", headers=auth_headers)
    tid = r.json()[0]["threadId"]

    r2 = api.get(f"{BASE_URL}/api/threads/{tid}", headers=auth_headers)
    assert r2.status_code == 200
    assert r2.json()["threadId"] == tid
    assert len(r2.json()["messages"]) >= 1

    r3 = api.patch(f"{BASE_URL}/api/emails/{tid}", headers=auth_headers, json={"star": True})
    assert r3.status_code == 200


def test_compose(api, auth_headers):
    r = api.post(f"{BASE_URL}/api/emails/compose", headers=auth_headers,
                 json={"to": "test@example.com", "subject": "TEST_compose",
                       "body": "hello from test", "account": "fmail"})
    assert r.status_code == 200
    d = r.json()
    assert d["folder"] == "sent"
    assert d["subject"] == "TEST_compose"


# ------------------- AI -------------------
def test_ai_understand(api, auth_headers):
    tid = api.get(f"{BASE_URL}/api/emails?folder=inbox", headers=auth_headers).json()[0]["threadId"]
    r = api.post(f"{BASE_URL}/api/ai/understand/{tid}", headers=auth_headers)
    assert r.status_code == 200, r.text
    d = r.json()
    assert "intent" in d and "keyInfo" in d


def test_ai_thread(api, auth_headers):
    tid = api.get(f"{BASE_URL}/api/emails?folder=inbox", headers=auth_headers).json()[0]["threadId"]
    r = api.post(f"{BASE_URL}/api/ai/thread/{tid}", headers=auth_headers)
    assert r.status_code == 200
    assert "summary" in r.json()


def test_ai_reply(api, auth_headers):
    tid = api.get(f"{BASE_URL}/api/emails?folder=inbox", headers=auth_headers).json()[0]["threadId"]
    r = api.post(f"{BASE_URL}/api/ai/reply", headers=auth_headers,
                 json={"threadId": tid, "tone": "Professional", "action": "reply"})
    assert r.status_code == 200
    assert "text" in r.json() and len(r.json()["text"]) > 0


def test_ai_ask(api, auth_headers):
    r = api.post(f"{BASE_URL}/api/ai/ask", headers=auth_headers,
                 json={"question": "What are my urgent items?"})
    assert r.status_code == 200
    assert "answer" in r.json()


def test_ai_email_to_task(api, auth_headers):
    tid = api.get(f"{BASE_URL}/api/emails?folder=inbox", headers=auth_headers).json()[0]["threadId"]
    r = api.post(f"{BASE_URL}/api/ai/email-to-task/{tid}", headers=auth_headers)
    assert r.status_code == 200
    assert "title" in r.json()


def test_ai_file_summary(api, auth_headers):
    files = api.get(f"{BASE_URL}/api/files", headers=auth_headers).json()
    assert files, "no seed files"
    fid = files[0]["id"]
    r = api.post(f"{BASE_URL}/api/ai/file-summary/{fid}", headers=auth_headers)
    assert r.status_code == 200
    assert "summary" in r.json()


# ------------------- tasks/events/contacts -------------------
def test_tasks_crud(api, auth_headers):
    r = api.get(f"{BASE_URL}/api/tasks", headers=auth_headers)
    assert r.status_code == 200 and len(r.json()) >= 5
    r2 = api.post(f"{BASE_URL}/api/tasks", headers=auth_headers,
                  json={"title": "TEST_task", "priority": "high"})
    assert r2.status_code == 200
    tid = r2.json()["id"]
    r3 = api.delete(f"{BASE_URL}/api/tasks/{tid}", headers=auth_headers)
    assert r3.status_code == 200


def test_events_crud(api, auth_headers):
    r = api.get(f"{BASE_URL}/api/events", headers=auth_headers)
    assert r.status_code == 200
    r2 = api.post(f"{BASE_URL}/api/events", headers=auth_headers,
                  json={"title": "TEST_event", "start": "2026-02-01T10:00:00Z"})
    assert r2.status_code == 200
    eid = r2.json()["id"]
    r3 = api.delete(f"{BASE_URL}/api/events/{eid}", headers=auth_headers)
    assert r3.status_code == 200


def test_contacts_and_graph(api, auth_headers):
    r = api.get(f"{BASE_URL}/api/contacts", headers=auth_headers)
    assert r.status_code == 200 and len(r.json()) >= 3
    cid = r.json()[0]["id"]
    r2 = api.get(f"{BASE_URL}/api/contacts/{cid}/graph", headers=auth_headers)
    assert r2.status_code == 200
    for k in ("contact", "emails", "meetings", "tasks", "memory"):
        assert k in r2.json()


def test_files_upload(api, auth_headers):
    r = api.get(f"{BASE_URL}/api/files", headers=auth_headers)
    assert r.status_code == 200 and len(r.json()) >= 3
    # multipart upload
    files_hdr = {"Authorization": auth_headers["Authorization"]}
    r2 = requests.post(f"{BASE_URL}/api/files",
                       headers=files_hdr,
                       data={"name": "TEST_upload.pdf", "type": "pdf", "size": "12 KB"})
    assert r2.status_code == 200
    assert r2.json()["name"] == "TEST_upload.pdf"


def test_memory_and_spaces(api, auth_headers):
    r = api.get(f"{BASE_URL}/api/memory", headers=auth_headers)
    assert r.status_code == 200 and len(r.json()) >= 3
    r2 = api.post(f"{BASE_URL}/api/memory", headers=auth_headers,
                  json={"kind": "Person", "title": "TEST_M", "detail": "A test person"})
    assert r2.status_code == 200
    mid = r2.json()["id"]
    r3 = api.delete(f"{BASE_URL}/api/memory/{mid}", headers=auth_headers)
    assert r3.status_code == 200

    r4 = api.get(f"{BASE_URL}/api/spaces", headers=auth_headers)
    assert r4.status_code == 200 and len(r4.json()) >= 3


# ------------------- meetings -------------------
def test_meetings(api, auth_headers):
    r = api.get(f"{BASE_URL}/api/meetings", headers=auth_headers)
    assert r.status_code == 200 and len(r.json()) >= 1
    mid = r.json()[0]["id"]

    r2 = api.get(f"{BASE_URL}/api/meetings/{mid}", headers=auth_headers)
    assert r2.status_code == 200

    r3 = api.post(f"{BASE_URL}/api/meetings", headers=auth_headers,
                  json={"title": "TEST_new_meeting", "mode": "General"})
    assert r3.status_code == 200
    new_id = r3.json()["id"]

    r4 = api.post(f"{BASE_URL}/api/meetings/{new_id}/notes", headers=auth_headers)
    assert r4.status_code == 200
    assert "summary" in r4.json()

    r5 = api.post(f"{BASE_URL}/api/meetings/{mid}/ask", headers=auth_headers,
                  json={"question": "What was the pricing floor?"})
    assert r5.status_code == 200
    assert "answer" in r5.json()


# ------------------- agents -------------------
def test_agents_marketplace_install_toggle_delete(api, auth_headers):
    r = api.get(f"{BASE_URL}/api/agents/marketplace", headers=auth_headers)
    assert r.status_code == 200 and len(r.json()) >= 5

    r2 = api.get(f"{BASE_URL}/api/agents/installed", headers=auth_headers)
    assert r2.status_code == 200

    r3 = api.post(f"{BASE_URL}/api/agents/install", headers=auth_headers,
                  json={"name": "Travel Agent"})
    assert r3.status_code in (200, 400)
    if r3.status_code == 200:
        aid = r3.json()["id"]
        r4 = api.post(f"{BASE_URL}/api/agents/{aid}/toggle", headers=auth_headers)
        assert r4.status_code == 200
        r5 = api.delete(f"{BASE_URL}/api/agents/{aid}", headers=auth_headers)
        assert r5.status_code == 200


# ------------------- representative -------------------
def test_representative(api, auth_headers):
    r = api.get(f"{BASE_URL}/api/representative", headers=auth_headers)
    assert r.status_code == 200
    r2 = api.put(f"{BASE_URL}/api/representative", headers=auth_headers,
                 json={"mode": "AI Assistant", "negotiationFloor": 60000})
    assert r2.status_code == 200
    assert r2.json()["mode"] == "AI Assistant"


# ------------------- misc -------------------
def test_search(api, auth_headers):
    r = api.get(f"{BASE_URL}/api/search?q=proposal", headers=auth_headers)
    assert r.status_code == 200
    d = r.json()
    assert any(len(d.get(k, [])) > 0 for k in ("emails", "tasks", "memory"))


def test_audit_and_notifications(api, auth_headers):
    r = api.get(f"{BASE_URL}/api/audit", headers=auth_headers)
    assert r.status_code == 200 and len(r.json()) >= 1
    r2 = api.get(f"{BASE_URL}/api/notifications", headers=auth_headers)
    assert r2.status_code == 200 and len(r2.json()) >= 1


def test_followups(api, auth_headers):
    r = api.get(f"{BASE_URL}/api/followups", headers=auth_headers)
    assert r.status_code == 200
    if r.json():
        fid = r.json()[0]["id"]
        r2 = api.post(f"{BASE_URL}/api/followups/{fid}/dismissed", headers=auth_headers)
        assert r2.status_code == 200


# ------------------- sarvam -------------------
def test_translate(api, auth_headers):
    r = api.post(f"{BASE_URL}/api/translate", headers=auth_headers,
                 json={"text": "Hello, how are you today?", "source": "en-IN", "target": "hi-IN"})
    # Accept success or graceful 502/503 (not 500)
    assert r.status_code in (200, 502, 503), f"unexpected {r.status_code}: {r.text}"
    if r.status_code == 200:
        assert "translated_text" in r.json() or "translated_texts" in r.json() or r.json()


def test_translate_same_lang(api, auth_headers):
    r = api.post(f"{BASE_URL}/api/translate", headers=auth_headers,
                 json={"text": "Hi", "source": "en-IN", "target": "en-IN"})
    assert r.status_code == 400


def test_voice_transcribe_synthetic(api, auth_headers):
    # send tiny dummy audio; should NOT 500
    files_hdr = {"Authorization": auth_headers["Authorization"]}
    files = {"file": ("t.m4a", b"\x00\x00\x00\x00fake", "audio/mp4")}
    r = requests.post(f"{BASE_URL}/api/voice/transcribe", headers=files_hdr,
                      data={"language_code": "hi-IN", "mode": "codemix"}, files=files)
    assert r.status_code in (200, 502, 503), f"unexpected {r.status_code}: {r.text[:300]}"


# ------------------- unauth -------------------
def test_unauth_blocked(api):
    r = api.get(f"{BASE_URL}/api/dashboard")
    assert r.status_code in (401, 403)
