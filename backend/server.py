"""Fmail — Personal Communication OS backend.
Unified layer: auth/identity, universal inbox, AI (classify/summarize/reply/ask),
tasks, calendar, contacts, files, meetings + copilot, memory, agents/marketplace,
spaces, decisions, commitments, follow-ups, audit log, notifications, dashboard,
plus Sarvam voice transcription & translation.
"""
import os
import uuid
import json
import logging
import hashlib
import secrets
import base64
import re
import asyncio
import urllib.parse
from email.message import EmailMessage
from email.utils import parseaddr
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Any

import jwt
import httpx
from fastapi import FastAPI, APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr
import bcrypt

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("fmail")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

JWT_SECRET = os.environ.get("JWT_SECRET", "dev")
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")
SARVAM_API_KEY = os.environ.get("SARVAM_API_KEY")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
RESEND_FROM_EMAIL = os.environ.get("RESEND_FROM_EMAIL")
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI")
TOKEN_ENCRYPTION_KEY = os.environ.get("TOKEN_ENCRYPTION_KEY")
FIREBASE_PROJECT_ID = os.environ.get("FIREBASE_PROJECT_ID", "fmail-a296f")
FIREBASE_SERVICE_ACCOUNT_JSON = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")

app = FastAPI(title="Fmail API")
api = APIRouter(prefix="/api")
security = HTTPBearer(auto_error=True)


# ----------------------------- helpers ---------------------------------------
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return str(uuid.uuid4())


def make_token(uid: str) -> str:
    payload = {"uid": uid, "exp": datetime.now(timezone.utc) + timedelta(days=30)}
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


async def current_user(creds: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    try:
        payload = jwt.decode(creds.credentials, JWT_SECRET, algorithms=["HS256"])
    except Exception:
        raise HTTPException(401, "Invalid or expired session")
    user = await db.users.find_one({"id": payload["uid"]}, {"_id": 0, "password": 0})
    if not user:
        raise HTTPException(401, "User not found")
    acct = await db.gmail_accounts.find_one({"uid": user["id"]}, {"_id": 0, "email": 1, "revoked": 1, "history_id": 1})
    user["gmailConnected"] = bool(acct) and not (acct or {}).get("revoked", False)
    user["gmailEmail"] = acct["email"] if acct else None
    # keep connectedAccounts in sync for UI
    accounts = [
        {"provider": "gmail", "email": acct["email"] if acct else "", "connected": user["gmailConnected"]},
    ]
    user["connectedAccounts"] = accounts
    return user


def _user_addr(user: dict) -> str:
    """The address Fmail sends/displays as — the connected Gmail, else the login email."""
    return user.get("gmailEmail") or user.get("email")


async def audit(uid: str, action: str, detail: str = "", actor: str = "You"):
    await db.audit.insert_one({
        "id": new_id(), "uid": uid, "action": action, "detail": detail,
        "actor": actor, "created_at": now_iso(),
    })


# ----------------------------- AI layer ---------------------------------------
async def llm_json(system: str, prompt: str, fallback: dict) -> dict:
    """Structured JSON generation with graceful fallback."""
    if not EMERGENT_LLM_KEY:
        return fallback
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=new_id(),
                       system_message=system + "\nReturn ONLY valid minified JSON. No markdown.")
        chat.with_model("openai", "gpt-5.4")
        resp = await chat.send_message(UserMessage(text=prompt))
        text = resp.strip()
        if text.startswith("```"):
            text = text.split("```")[1].replace("json", "", 1).strip()
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start:end + 1])
        return fallback
    except Exception as e:
        logger.warning(f"llm_json failed: {e}")
        return fallback


async def llm_text(system: str, prompt: str, fallback: str = "") -> str:
    if not EMERGENT_LLM_KEY:
        return fallback
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=new_id(), system_message=system)
        chat.with_model("openai", "gpt-5.4")
        resp = await chat.send_message(UserMessage(text=prompt))
        return (resp or fallback).strip()
    except Exception as e:
        logger.warning(f"llm_text failed: {e}")
        return fallback


# ----------------------------- models -----------------------------------------
class SignupIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str
    code: Optional[str] = None


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class ProfileIn(BaseModel):
    name: Optional[str] = None
    signature: Optional[str] = None
    photo: Optional[str] = None
    darkMode: Optional[str] = None
    aiEnabled: Optional[bool] = None
    memoryEnabled: Optional[bool] = None


class ComposeIn(BaseModel):
    to: str
    subject: str
    body: str
    cc: Optional[str] = ""
    bcc: Optional[str] = ""
    attachments: List[dict] = []  # [{name, type, size, data(base64)}]
    account: Optional[str] = "fmail"
    threadId: Optional[str] = None
    draftId: Optional[str] = None
    draft: Optional[bool] = False


class AiComposeIn(BaseModel):
    instruction: str
    tone: str = "Professional"
    to: Optional[str] = ""
    context: Optional[str] = ""


class OtpRequestIn(BaseModel):
    email: EmailStr
    purpose: str = "signup"  # signup | reset


class OtpVerifyIn(BaseModel):
    email: EmailStr
    code: str
    purpose: str = "signup"


class ResetPasswordIn(BaseModel):
    email: EmailStr
    code: str
    password: str = Field(min_length=6)


class PermissionsIn(BaseModel):
    permissions: dict


class PatchEmailIn(BaseModel):
    star: Optional[bool] = None
    important: Optional[bool] = None
    read: Optional[bool] = None
    folder: Optional[str] = None
    category: Optional[str] = None
    space: Optional[str] = None


class AskIn(BaseModel):
    question: str


class ReplyIn(BaseModel):
    threadId: str
    tone: str = "Professional"
    action: str = "reply"  # reply|rewrite|shorten|expand|grammar|translate|professional
    draft: Optional[str] = None


class TaskIn(BaseModel):
    title: str
    due: Optional[str] = None
    priority: str = "medium"
    labels: List[str] = []
    project: Optional[str] = None
    notes: Optional[str] = None
    subtasks: List[dict] = []
    done: Optional[bool] = False
    id: Optional[str] = None


class EventIn(BaseModel):
    title: str
    start: str
    end: Optional[str] = None
    location: Optional[str] = None
    attendees: List[str] = []
    notes: Optional[str] = None
    id: Optional[str] = None


class ContactIn(BaseModel):
    name: str
    email: str
    company: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    id: Optional[str] = None


class MemoryIn(BaseModel):
    kind: str
    title: str
    detail: str
    id: Optional[str] = None


class SpaceIn(BaseModel):
    name: str
    color: Optional[str] = "#FF5E00"
    id: Optional[str] = None


class MeetingIn(BaseModel):
    title: str
    start: Optional[str] = None
    mode: str = "General"
    attendees: List[str] = []
    aiCopilot: bool = True
    id: Optional[str] = None


class TranslateIn(BaseModel):
    text: str
    source: str = "en-IN"
    target: str = "hi-IN"


class GoogleSignInIn(BaseModel):
    id_token: str
    choice: str = "connect"


class GoogleConnectIn(BaseModel):
    code: str


class PushTokenIn(BaseModel):
    token: str = Field(min_length=20)
    platform: str = Field(default="android", pattern="^(android|ios)$")


class AnalyticsEventIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    params: dict = {}


class FeedbackIn(BaseModel):
    message: str = Field(min_length=5, max_length=5000)
    category: str = Field(default="general", max_length=40)


# ----------------------------- seed data --------------------------------------
def seed_for(uid: str, handle: str, name: str):
    tnow = datetime.now(timezone.utc)

    def iso(delta_hours):
        return (tnow - timedelta(hours=delta_hours)).isoformat()

    def fut(hours):
        return (tnow + timedelta(hours=hours)).isoformat()

    emails = [
        dict(subject="Proposal review — please send by Friday", sender="Rahul Verma",
             senderEmail="rahul@brightlabs.in", account="gmail", category="Work",
             aiLabel="Action Required", important=True, unread=True, star=False, folder="inbox",
             snippet="Hi, could you please send the final proposal by Friday? The client wants to review pricing before our call.",
             body="Hi " + name + ",\n\nCould you please send the final proposal by Friday? The client wants to review the pricing section before our call next week. Also confirm if we can meet tomorrow at 3 PM to align.\n\nThanks,\nRahul", hago=3),
        dict(subject="Invoice #INV-2043 due on Oct 28", sender="Zylo Billing",
             senderEmail="billing@zylo.com", account="fmail", category="Finance",
             aiLabel="Finance", important=True, unread=True, star=True, folder="inbox",
             snippet="Your invoice of ₹42,000 is due on Oct 28. Please complete the payment to avoid service interruption.",
             body="Dear Customer,\n\nYour invoice #INV-2043 for ₹42,000 is due on Oct 28, 2026. Kindly complete the payment to avoid any interruption to your subscription.\n\nRegards,\nZylo Billing Team", hago=8),
        dict(subject="Interview scheduled — Frontend Engineer", sender="Careers @ Nimbus",
             senderEmail="careers@nimbus.io", account="outlook", category="Work",
             aiLabel="Important", important=True, unread=False, star=False, folder="inbox",
             snippet="Congrats! Your interview is scheduled for Thursday 11 AM. Please confirm your availability.",
             body="Hello,\n\nCongratulations on clearing the screening round! Your technical interview is scheduled for Thursday at 11 AM IST. Please confirm your availability by replying to this email.\n\nBest,\nNimbus Talent", hago=20),
        dict(subject="Weekend Sale — 50% off everything!", sender="TrendKart",
             senderEmail="offers@trendkart.com", account="gmail", category="Shopping",
             aiLabel="Promotional", important=False, unread=True, star=False, folder="inbox",
             snippet="Flat 50% off this weekend only. Shop now before stocks run out!",
             body="Huge weekend sale! Flat 50% off across all categories. Use code WEEKEND50 at checkout. Offer valid till Sunday.\n\nUnsubscribe anytime.", hago=30),
        dict(subject="Startup weekly digest — growth up 18%", sender="Founders Brief",
             senderEmail="hello@foundersbrief.com", account="fmail", category="Startup",
             aiLabel="Newsletter", important=False, unread=True, star=False, folder="inbox",
             snippet="This week: MRR grew 18%, two new hires, and the beta launch is on track.",
             body="Weekly digest:\n- MRR grew 18% week over week\n- Onboarded 2 engineers\n- Beta launch on track for Oct 10\n- Investor update due next Monday", hago=48),
        dict(subject="Waiting on your reply — design handoff", sender="Ananya Rao",
             senderEmail="ananya@brightlabs.in", account="gmail", category="Work",
             aiLabel="Waiting for Reply", important=False, unread=False, star=False, folder="inbox",
             snippet="Just following up on the design handoff. Let me know when you can review the Figma file.",
             body="Hey " + name + ",\n\nJust following up on the design handoff from last week. Could you review the Figma file and share feedback? We're blocked on your inputs for the dashboard screens.\n\nThanks,\nAnanya", hago=72),
        dict(subject="Your OTP and account security alert", sender="SecureBank",
             senderEmail="alerts@secure-bank-verify.co", account="gmail", category="Finance",
             aiLabel="Urgent", important=False, unread=True, star=False, folder="inbox", suspicious=True,
             snippet="Unusual login detected. Verify your account immediately by clicking the link or your account will be locked.",
             body="URGENT: Unusual login detected on your account. Verify immediately at http://secure-bank-verify.co/login or your account will be permanently locked within 24 hours.", hago=5),
        dict(subject="Lunch this weekend?", sender="Mom",
             senderEmail="mom@family.com", account="fmail", category="Personal",
             aiLabel="Personal", important=False, unread=False, star=True, folder="inbox",
             snippet="Are you free for lunch this Sunday? Let me know, beta.",
             body="Hi beta,\n\nAre you free for lunch this Sunday? We could try that new place near the park. Let me know!\n\nLove, Mom", hago=15),
        dict(subject="College project submission reminder", sender="Prof. Menon",
             senderEmail="menon@univ.edu", account="outlook", category="College",
             aiLabel="Action Required", important=False, unread=True, star=False, folder="inbox",
             snippet="Reminder: final project report is due next Wednesday. Submit via the portal.",
             body="Dear students,\n\nThis is a reminder that your final project report is due next Wednesday by 5 PM. Please submit through the portal. Late submissions will not be accepted.\n\nProf. Menon", hago=26),
        dict(subject="Re: Q4 roadmap discussion", sender="Kabir Singh",
             senderEmail="kabir@brightlabs.in", account="gmail", category="Work",
             aiLabel="FYI", important=False, unread=False, star=False, folder="inbox",
             snippet="Great notes from the sync. I've added a couple of items to the roadmap doc.",
             body="Thanks for the sync notes. I added two items to the roadmap doc — the analytics revamp and the mobile onboarding flow. Let's finalize in the next review.", hago=100),
    ]

    docs = []
    thread_map = {}
    for e in emails:
        tid = new_id()
        mid = new_id()
        thread_map[e["subject"]] = tid
        docs.append({
            "id": mid, "threadId": tid, "uid": uid,
            "subject": e["subject"], "sender": e["sender"], "senderEmail": e["senderEmail"],
            "to": handle + "@fmails.in", "account": e["account"], "category": e["category"],
            "aiLabel": e["aiLabel"], "important": e["important"], "unread": e["unread"],
            "star": e["star"], "folder": e["folder"], "snippet": e["snippet"], "body": e["body"],
            "suspicious": e.get("suspicious", False), "space": None,
            "created_at": iso(e["hago"]), "outgoing": False,
        })
    # a sent example
    tid_sent = new_id()
    docs.append({
        "id": new_id(), "threadId": tid_sent, "uid": uid,
        "subject": "Kickoff notes for the new client", "sender": name,
        "senderEmail": handle + "@fmails.in", "to": "rahul@brightlabs.in",
        "account": "fmail", "category": "Work", "aiLabel": "FYI", "important": False,
        "unread": False, "star": False, "folder": "sent", "snippet": "Sharing the kickoff notes and next steps.",
        "body": "Hi Rahul,\n\nSharing the kickoff notes and next steps from today. Let's align on timelines this week.\n\nBest,\n" + name,
        "suspicious": False, "space": None, "created_at": iso(90), "outgoing": True,
    })

    contacts = [
        dict(name="Rahul Verma", email="rahul@brightlabs.in", company="Bright Labs", role="Product Lead", phone="+91 98100 11111"),
        dict(name="Ananya Rao", email="ananya@brightlabs.in", company="Bright Labs", role="Designer", phone="+91 98100 22222"),
        dict(name="Kabir Singh", email="kabir@brightlabs.in", company="Bright Labs", role="Engineer", phone="+91 98100 33333"),
        dict(name="Prof. Menon", email="menon@univ.edu", company="University", role="Professor", phone=""),
    ]
    contact_docs = [{"id": new_id(), "uid": uid, **c, "created_at": now_iso()} for c in contacts]

    tasks = [
        dict(title="Send final proposal to client", due=fut(30), priority="high", labels=["Work"], project="Bright Labs", done=False, source="Email: Proposal review"),
        dict(title="Pay invoice #INV-2043 (₹42,000)", due=fut(60), priority="high", labels=["Finance"], project=None, done=False, source="Email: Invoice"),
        dict(title="Review Figma design handoff", due=fut(48), priority="medium", labels=["Work"], project="Bright Labs", done=False, source="Email: Ananya"),
        dict(title="Submit college project report", due=fut(120), priority="medium", labels=["College"], project=None, done=False, source="Email: Prof. Menon"),
        dict(title="Prepare investor update", due=fut(80), priority="low", labels=["Startup"], project="Fundraise", done=False, source=None),
    ]
    task_docs = [{"id": new_id(), "uid": uid, "subtasks": [], "notes": None, **t, "created_at": now_iso()} for t in tasks]

    events = [
        dict(title="Client proposal call", start=fut(20), end=fut(21), location="Fmail Meet", attendees=["rahul@brightlabs.in"], notes="Discuss pricing and roadmap"),
        dict(title="Frontend interview — Nimbus", start=fut(44), end=fut(45), location="Fmail Meet", attendees=["careers@nimbus.io"], notes=None),
        dict(title="Team standup", start=fut(2), end=fut(2.5), location="Fmail Meet", attendees=["kabir@brightlabs.in", "ananya@brightlabs.in"], notes=None),
        dict(title="Lunch with Mom", start=fut(96), end=fut(98), location="City Park", attendees=[], notes=None),
    ]
    event_docs = [{"id": new_id(), "uid": uid, **ev, "created_at": now_iso()} for ev in events]

    files = [
        dict(name="Client_Proposal_v3.pdf", type="pdf", size="248 KB", summary=None, source="Email: Proposal review"),
        dict(name="Invoice_INV-2043.pdf", type="pdf", size="88 KB", summary=None, source="Email: Invoice"),
        dict(name="Product_Roadmap.pptx", type="presentation", size="1.2 MB", summary=None, source="Meeting: Q4 planning"),
        dict(name="Dashboard_Designs.fig", type="design", size="4.5 MB", summary=None, source="Email: Ananya"),
    ]
    file_docs = [{"id": new_id(), "uid": uid, **f, "created_at": now_iso()} for f in files]

    meetings = [
        dict(title="Q4 Planning Review", mode="Project Review", start=iso(120), status="completed", aiCopilot=True,
             attendees=["kabir@brightlabs.in", "ananya@brightlabs.in", "rahul@brightlabs.in"],
             transcript=[
                 {"speaker": "Rahul", "text": "Let's finalize the Q4 roadmap. I think we should launch the beta on October 10.", "t": "00:12"},
                 {"speaker": "Ananya", "text": "The dashboard designs will be ready by the 5th, so that works.", "t": "01:04"},
                 {"speaker": name, "text": "Agreed. I'll own the proposal and send it to the client by Friday.", "t": "02:20"},
                 {"speaker": "Kabir", "text": "I'll handle the analytics revamp. Can we get the pricing approved above 50k?", "t": "03:41"},
                 {"speaker": "Rahul", "text": "Yes, keep the floor at 50,000. Do not go below that without approval.", "t": "04:10"},
             ],
             notes={
                 "summary": "The team finalized the Q4 roadmap, agreed on a beta launch date, and assigned ownership for the proposal, designs, and analytics work.",
                 "keyPoints": ["Beta launch targeted for October 10", "Dashboard designs ready by Oct 5", "Pricing floor set at ₹50,000"],
                 "decisions": ["Launch beta on October 10", "Keep pricing floor at ₹50,000"],
                 "actionItems": ["Send proposal to client by Friday (You)", "Deliver dashboard designs by Oct 5 (Ananya)", "Complete analytics revamp (Kabir)"],
                 "questions": ["Will the client approve pricing above ₹50,000?"],
                 "nextSteps": ["Client proposal call", "Design review on Oct 5"],
             }),
    ]
    meeting_docs = [{"id": new_id(), "uid": uid, **m, "created_at": now_iso()} for m in meetings]

    memory = [
        dict(kind="Person", title="Rahul Verma", detail="Product Lead at Bright Labs. Main client contact. Prefers concise updates and cares about pricing."),
        dict(kind="Organization", title="Bright Labs", detail="Primary client. Working on Q4 dashboard revamp and proposal."),
        dict(kind="Project", title="Beta Launch", detail="Beta launch targeted October 10. Pricing floor ₹50,000."),
        dict(kind="Decision", title="Pricing floor ₹50,000", detail="Decided in Q4 Planning Review. Do not go below without approval."),
        dict(kind="Commitment", title="Send proposal by Friday", detail="You committed to send the final proposal to the client by Friday."),
    ]
    memory_docs = [{"id": new_id(), "uid": uid, **m, "created_at": now_iso()} for m in memory]

    spaces = [
        dict(name="Work", color="#FF5E00"), dict(name="Startup", color="#2F6FED"),
        dict(name="Personal", color="#1E9E5A"), dict(name="College", color="#C98A00"),
    ]
    space_docs = [{"id": new_id(), "uid": uid, **s, "created_at": now_iso()} for s in spaces]

    decisions = [
        dict(text="Launch beta on October 10", source="Q4 Planning Review", project="Beta Launch", date=iso(120)),
        dict(text="Keep pricing floor at ₹50,000", source="Q4 Planning Review", project="Beta Launch", date=iso(120)),
    ]
    decision_docs = [{"id": new_id(), "uid": uid, **d, "created_at": now_iso()} for d in decisions]

    commitments = [
        dict(text="Send the final proposal to the client", owner="You", deadline="Friday", source="Q4 Planning Review", status="pending"),
        dict(text="Deliver dashboard designs", owner="Ananya", deadline="Oct 5", source="Q4 Planning Review", status="pending"),
    ]
    commitment_docs = [{"id": new_id(), "uid": uid, **c, "created_at": now_iso()} for c in commitments]

    followups = [
        dict(person="Ananya Rao", email="ananya@brightlabs.in", subject="Design handoff", days=3, threadId=thread_map.get("Waiting on your reply — design handoff")),
        dict(person="Rahul Verma", email="rahul@brightlabs.in", subject="Kickoff notes for the new client", days=4, threadId=tid_sent),
    ]
    followup_docs = [{"id": new_id(), "uid": uid, **f, "status": "open", "created_at": now_iso()} for f in followups]

    installed = ["Follow-up Agent", "Meeting Agent", "Finance Agent"]
    agent_docs = [{"id": new_id(), "uid": uid, "name": n, "enabled": True, "created_at": now_iso(),
                   "memory": [], "custom": False} for n in installed]

    notifications = [
        dict(title="Invoice due soon", body="Invoice #INV-2043 (₹42,000) is due on Oct 28", kind="finance"),
        dict(title="Waiting for Ananya — 3 days", body="No reply on the design handoff", kind="followup"),
        dict(title="Meeting starting soon", body="Team standup in 2 hours", kind="meeting"),
    ]
    notif_docs = [{"id": new_id(), "uid": uid, **n, "read": False, "created_at": now_iso()} for n in notifications]

    return dict(emails=docs, contacts=contact_docs, tasks=task_docs, events=event_docs,
                files=file_docs, meetings=meeting_docs, memory=memory_docs, spaces=space_docs,
                decisions=decision_docs, commitments=commitment_docs, followups=followup_docs,
                agents=agent_docs, notifications=notif_docs)


# ----------------------------- auth routes ------------------------------------
@api.get("/")
async def root():
    return {"app": "Fmail", "status": "ok"}


@api.post("/auth/signup")
async def signup(body: SignupIn):
    """Create a Fmail account (email/password). Users connect their real Gmail after signup."""
    email = body.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(400, "An account with this email already exists")
    # OTP is only enforced when email delivery is configured.
    if RESEND_API_KEY and RESEND_FROM_EMAIL:
        if not body.code:
            raise HTTPException(400, "Please verify your email with the code we sent.")
        await _verify_code(email, body.code, "signup")
    uid = new_id()
    pw = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
    user = {
        "id": uid, "email": email, "password": pw, "name": body.name,
        "photo": None, "signature": "Sent with Fmail", "aliases": [],
        "connectedAccounts": [{"provider": "gmail", "email": "", "connected": False}],
        "permissions": {"notifications": True, "camera": False, "microphone": False, "contacts": False, "storage": False},
        "aiEnabled": True, "memoryEnabled": True, "darkMode": "system",
        "created_at": now_iso(),
    }
    await db.users.insert_one(user)
    await db.otps.delete_one({"email": email, "purpose": "signup"})
    await audit(uid, "Account created", email)
    token = make_token(uid)
    user.pop("password"); user.pop("_id", None)
    return {"token": token, "user": user}


@api.post("/auth/login")
async def login(body: LoginIn):
    user = await db.users.find_one({"email": body.email.lower()})
    if not user or not bcrypt.checkpw(body.password.encode(), user["password"].encode()):
        raise HTTPException(401, "Incorrect email or password")
    token = make_token(user["id"])
    user.pop("password"); user.pop("_id", None)
    return {"token": token, "user": user}


@api.get("/auth/me")
async def me(user: dict = Depends(current_user)):
    return user


@api.put("/auth/profile")
async def update_profile(body: ProfileIn, user: dict = Depends(current_user)):
    updates = {k: v for k, v in body.dict().items() if v is not None}
    if updates:
        await db.users.update_one({"id": user["id"]}, {"$set": updates})
    fresh = await db.users.find_one({"id": user["id"]}, {"_id": 0, "password": 0})
    return fresh


@api.put("/auth/permissions")
async def set_permissions(body: PermissionsIn, user: dict = Depends(current_user)):
    await db.users.update_one({"id": user["id"]}, {"$set": {"permissions": body.permissions}})
    await audit(user["id"], "Permissions updated", ", ".join([k for k, v in body.permissions.items() if v]))
    return await db.users.find_one({"id": user["id"]}, {"_id": 0, "password": 0})


@api.delete("/auth/account")
async def delete_account(user: dict = Depends(current_user)):
    """Permanently delete the account and ALL associated data."""
    uid = user["id"]
    collections = ["emails", "contacts", "tasks", "events", "files", "meetings", "memory",
                   "spaces", "decisions", "commitments", "followups", "agents", "notifications",
                   "audit", "ai_cache", "ai_chat", "representative", "otps"]
    for coll in collections:
        await db[coll].delete_many({"uid": uid})
    await db.users.delete_one({"id": uid})
    logger.info(f"Account permanently deleted: {uid}")
    return {"ok": True, "deleted": True}


# ----------------------------- OTP / email verification -----------------------
def _gen_code() -> str:
    return f"{secrets.randbelow(1000000):06d}"


async def _send_email_code(to_email: str, code: str, purpose: str) -> None:
    """Send a real OTP through Resend. Never return a code to a client."""
    if not RESEND_API_KEY or not RESEND_FROM_EMAIL:
        raise HTTPException(503, "Email verification is temporarily unavailable. Please try again later.")
    action = "verify your Fmail account" if purpose == "signup" else "reset your Fmail password"
    html = (
        "<div style='font-family:Arial,sans-serif;max-width:520px;margin:auto'>"
        "<h2>Fmail verification</h2>"
        f"<p>Use this code to {action}:</p>"
        f"<p style='font-size:32px;font-weight:700;letter-spacing:8px'>{code}</p>"
        "<p>This code expires in 10 minutes. If you did not request it, you can ignore this email.</p>"
        "</div>"
    )
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"},
                json={"from": RESEND_FROM_EMAIL, "to": [to_email], "subject": "Your Fmail verification code", "html": html},
            )
        if response.status_code >= 400:
            logger.warning("Resend rejected OTP email with status %s", response.status_code)
            raise HTTPException(503, "We could not send the verification email. Please try again later.")
    except HTTPException:
        raise
    except httpx.RequestError:
        raise HTTPException(503, "Email delivery is temporarily unavailable. Please try again later.")


@api.post("/auth/request-otp")
async def request_otp(body: OtpRequestIn):
    email = body.email.lower()
    if body.purpose not in ("signup", "reset"):
        raise HTTPException(400, "Invalid verification purpose.")
    if body.purpose == "reset" and not await db.users.find_one({"email": email}):
        # Keep reset responses non-enumerating, but still do not claim an email was sent.
        return {"sent": True, "delivered": False}
    if body.purpose == "signup" and await db.users.find_one({"email": email}):
        raise HTTPException(400, "An account with this email already exists")
    existing = await db.otps.find_one({"email": email, "purpose": body.purpose})
    now = datetime.now(timezone.utc)
    if existing:
        last = datetime.fromisoformat(existing["last_sent"])
        if (now - last).total_seconds() < 30:
            raise HTTPException(429, "Please wait a few seconds before requesting another code.")
        if existing.get("send_count", 0) >= 5 and (now - datetime.fromisoformat(existing["created_at"])).total_seconds() < 3600:
            raise HTTPException(429, "Too many code requests. Please try again later.")
    code = _gen_code()
    await _send_email_code(email, code, body.purpose)
    doc = {
        "email": email, "purpose": body.purpose, "code_hash": hashlib.sha256(code.encode()).hexdigest(),
        "expires_at": (now + timedelta(minutes=10)).isoformat(), "attempts": 0, "verified": False,
        "send_count": (existing.get("send_count", 0) + 1) if existing else 1,
        "last_sent": now.isoformat(), "created_at": existing["created_at"] if existing else now.isoformat(),
    }
    await db.otps.update_one({"email": email, "purpose": body.purpose}, {"$set": doc}, upsert=True)
    return {"sent": True, "delivered": True}


async def _verify_code(email: str, code: str, purpose: str) -> bool:
    rec = await db.otps.find_one({"email": email, "purpose": purpose})
    if not rec:
        raise HTTPException(400, "Please request a verification code first.")
    if rec.get("attempts", 0) >= 5:
        raise HTTPException(429, "Too many incorrect attempts. Please request a new code.")
    if datetime.now(timezone.utc) > datetime.fromisoformat(rec["expires_at"]):
        raise HTTPException(400, "This code has expired. Please request a new one.")
    if hashlib.sha256(code.encode()).hexdigest() != rec["code_hash"]:
        await db.otps.update_one({"email": email, "purpose": purpose}, {"$inc": {"attempts": 1}})
        raise HTTPException(400, "Incorrect code. Please check and try again.")
    await db.otps.update_one({"email": email, "purpose": purpose}, {"$set": {"verified": True}})
    return True


@api.post("/auth/verify-otp")
async def verify_otp(body: OtpVerifyIn):
    await _verify_code(body.email.lower(), body.code, body.purpose)
    return {"verified": True}


@api.post("/auth/reset-password")
async def reset_password(body: ResetPasswordIn):
    email = body.email.lower()
    await _verify_code(email, body.code, "reset")
    user = await db.users.find_one({"email": email})
    if not user:
        raise HTTPException(404, "Account not found")
    pw = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
    await db.users.update_one({"id": user["id"]}, {"$set": {"password": pw}})
    await db.otps.delete_one({"email": email, "purpose": "reset"})
    await audit(user["id"], "Password reset", "Via verification code")
    token = make_token(user["id"])
    user.pop("password"); user.pop("_id", None)
    return {"token": token, "user": user}


# ----------------------------- production integrations -----------------------
def _fernet():
    if not TOKEN_ENCRYPTION_KEY:
        raise HTTPException(503, "Secure mailbox storage is not configured.")
    try:
        from cryptography.fernet import Fernet
        return Fernet(TOKEN_ENCRYPTION_KEY.encode())
    except Exception:
        raise HTTPException(503, "Secure mailbox storage is not configured correctly.")


def _google_ready() -> bool:
    return bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET and GOOGLE_REDIRECT_URI)


async def _google_tokens(code: str) -> dict:
    if not _google_ready():
        raise HTTPException(503, "Google integration is not configured for this Fmail project.")
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post("https://oauth2.googleapis.com/token", data={
                "code": code, "client_id": GOOGLE_CLIENT_ID, "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI, "grant_type": "authorization_code",
            })
        if response.status_code >= 400:
            raise HTTPException(400, "Google authorization expired or was denied. Please connect again.")
        return response.json()
    except HTTPException:
        raise
    except httpx.RequestError:
        raise HTTPException(503, "Google is temporarily unavailable. Please try again.")


async def _google_userinfo(access_token: str) -> dict:
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get("https://www.googleapis.com/oauth2/v3/userinfo", headers={"Authorization": f"Bearer {access_token}"})
    if response.status_code >= 400:
        raise HTTPException(401, "Google authorization is no longer valid. Please connect again.")
    return response.json()


async def _gmail_access_token(account: dict) -> str:
    expires_at = datetime.fromisoformat(account.get("expires_at", "1970-01-01T00:00:00+00:00"))
    if account.get("access_token") and expires_at > datetime.now(timezone.utc) + timedelta(minutes=2):
        return _fernet().decrypt(account["access_token"].encode()).decode()
    refresh_enc = account.get("refresh_token")
    if not refresh_enc:
        await _mark_revoked(account)
        raise HTTPException(401, "Gmail access expired. Please reconnect your Google account.")
    refresh = _fernet().decrypt(refresh_enc.encode()).decode()
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post("https://oauth2.googleapis.com/token", data={
            "client_id": GOOGLE_CLIENT_ID, "client_secret": GOOGLE_CLIENT_SECRET,
            "refresh_token": refresh, "grant_type": "refresh_token",
        })
    if response.status_code >= 400:
        await _mark_revoked(account)
        raise HTTPException(401, "Gmail access expired. Please reconnect your Google account.")
    data = response.json()
    account["access_token"] = _fernet().encrypt(data["access_token"].encode()).decode()
    account["expires_at"] = (datetime.now(timezone.utc) + timedelta(seconds=int(data.get("expires_in", 3600)))).isoformat()
    await db.gmail_accounts.update_one({"id": account["id"]}, {"$set": {"access_token": account["access_token"], "expires_at": account["expires_at"], "revoked": False}})
    return data["access_token"]


async def _mark_revoked(account: dict) -> None:
    await db.gmail_accounts.update_one({"id": account["id"]}, {"$set": {"revoked": True}})
    await db.users.update_one({"id": account["uid"]}, {"$set": {"connectedAccounts.0.connected": False}})


@api.get("/auth/google/config")
async def google_config():
    return {"configured": _google_ready(), "provider": "google", "project": FIREBASE_PROJECT_ID}


GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"
GMAIL_SCOPE = "openid email profile https://www.googleapis.com/auth/gmail.modify"


def _encrypt(value: str) -> str:
    return _fernet().encrypt((value or "").encode()).decode()


async def _store_gmail_account(uid: str, info: dict, tokens: dict) -> dict:
    """Create/update a Gmail account record, preserving an existing refresh token if Google omits one."""
    email = info["email"].lower()
    existing = await db.gmail_accounts.find_one({"uid": uid, "email": email})
    refresh = tokens.get("refresh_token")
    account = {
        "id": (existing or {}).get("id", new_id()), "uid": uid, "email": email,
        "access_token": _encrypt(tokens["access_token"]),
        "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=int(tokens.get("expires_in", 3600)))).isoformat(),
        "revoked": False, "created_at": (existing or {}).get("created_at", now_iso()),
        "history_id": (existing or {}).get("history_id"),
    }
    if refresh:
        account["refresh_token"] = _encrypt(refresh)
    elif existing and existing.get("refresh_token"):
        account["refresh_token"] = existing["refresh_token"]
    await db.gmail_accounts.update_one({"uid": uid, "email": email}, {"$set": account}, upsert=True)
    await db.users.update_one({"id": uid}, {"$set": {"connectedAccounts": [{"provider": "gmail", "email": email, "connected": True}]}})
    return account


def _app_redirect(path: str, **params) -> RedirectResponse:
    scheme = os.environ.get("EXPO_APP_SCHEME", "frontend")
    query = ("?" + urllib.parse.urlencode(params)) if params else ""
    return RedirectResponse(f"{scheme}://{path}{query}")


# ---- low-level Gmail HTTP with revoke handling ----
async def _gmail_request(account: dict, method: str, path: str, **kwargs) -> httpx.Response:
    token = await _gmail_access_token(account)
    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"Bearer {token}"
    async with httpx.AsyncClient(timeout=40) as client:
        resp = await client.request(method, GMAIL_API + path, headers=headers, **kwargs)
    if resp.status_code in (401, 403):
        await _mark_revoked(account)
        raise HTTPException(401, "Gmail access was revoked. Please reconnect your Google account.")
    return resp


def _b64url_decode(data: str) -> bytes:
    if not data:
        return b""
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def _html_to_text(html: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?</\1>", "", html or "")
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</p>", "\n\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text).replace("&gt;", ">").replace("&quot;", '"').replace("&#39;", "'")
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _parse_parts(payload: dict):
    text_parts, html_parts, attachments = [], [], []

    def walk(part):
        mime = part.get("mimeType", "")
        body = part.get("body", {})
        filename = part.get("filename") or ""
        if part.get("parts"):
            for p in part["parts"]:
                walk(p)
            return
        data = body.get("data")
        if filename and (body.get("attachmentId") or data):
            attachments.append({"name": filename, "mimeType": mime, "size": body.get("size", 0),
                                "attachmentId": body.get("attachmentId")})
        elif mime == "text/plain" and data:
            text_parts.append(_b64url_decode(data).decode("utf-8", "ignore"))
        elif mime == "text/html" and data:
            html_parts.append(_b64url_decode(data).decode("utf-8", "ignore"))

    walk(payload or {})
    return "\n".join(text_parts).strip(), "\n".join(html_parts).strip(), attachments


def _folder_from_labels(labels: list) -> str:
    if "TRASH" in labels:
        return "trash"
    if "DRAFT" in labels:
        return "drafts"
    if "SENT" in labels:
        return "sent"
    if "INBOX" in labels:
        return "inbox"
    return "archive"


def _gmail_label(aiLabel: str) -> str:
    return aiLabel


def _email_doc(uid: str, msg: dict) -> dict:
    payload = msg.get("payload", {})
    headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}
    labels = msg.get("labelIds", [])
    text, html, attachments = _parse_parts(payload)
    from_name, from_email = parseaddr(headers.get("from", ""))
    internal = msg.get("internalDate")
    try:
        created = datetime.fromtimestamp(int(internal) / 1000, timezone.utc).isoformat() if internal else now_iso()
    except Exception:
        created = now_iso()
    body_plain = text or _html_to_text(html)
    return {
        "id": new_id(), "threadId": msg.get("threadId", new_id()), "uid": uid,
        "providerMessageId": msg["id"], "messageIdHeader": headers.get("message-id", ""),
        "references": headers.get("references", "") or headers.get("message-id", ""),
        "subject": headers.get("subject", "(no subject)"),
        "sender": from_name or from_email or "Unknown sender", "senderEmail": from_email,
        "to": headers.get("to", ""), "cc": headers.get("cc", ""), "bcc": "",
        "account": "gmail", "category": "Work", "aiLabel": "FYI",
        "important": "IMPORTANT" in labels, "unread": "UNREAD" in labels, "star": "STARRED" in labels,
        "folder": _folder_from_labels(labels), "snippet": msg.get("snippet", ""),
        "body": body_plain, "bodyHtml": html, "attachments": attachments, "labels": labels,
        "outgoing": "SENT" in labels, "space": None, "suspicious": False, "created_at": created,
    }


async def _upsert_email(uid: str, msg: dict) -> dict:
    doc = _email_doc(uid, msg)
    existing = await db.emails.find_one({"uid": uid, "providerMessageId": doc["providerMessageId"]}, {"_id": 0, "id": 1})
    if existing:
        doc["id"] = existing["id"]
        await db.emails.update_one(
            {"uid": uid, "providerMessageId": doc["providerMessageId"]},
            {"$set": {k: doc[k] for k in ("subject", "sender", "senderEmail", "to", "cc", "important",
                                          "unread", "star", "folder", "snippet", "body", "bodyHtml",
                                          "attachments", "labels", "messageIdHeader", "references", "outgoing")}},
        )
        return doc
    await db.emails.insert_one(dict(doc))
    doc.pop("_id", None)
    return doc


async def _gmail_get_message(account: dict, message_id: str, fmt: str = "full") -> Optional[dict]:
    resp = await _gmail_request(account, "GET", f"/messages/{message_id}", params={"format": fmt})
    if resp.status_code >= 400:
        return None
    return resp.json()


async def _gmail_list_ids(account: dict, label: str, max_results: int = 25) -> list:
    resp = await _gmail_request(account, "GET", "/messages",
                                params={"labelIds": label, "maxResults": max_results})
    if resp.status_code >= 400:
        return []
    return [m["id"] for m in resp.json().get("messages", [])]


async def _gmail_profile(account: dict) -> dict:
    resp = await _gmail_request(account, "GET", "/profile")
    return resp.json() if resp.status_code < 400 else {}


async def _sync_gmail_account(account: dict, notify: bool = True) -> int:
    """Incremental when a historyId exists, otherwise a bounded first sync. Returns # of new inbox mails."""
    uid = account["uid"]
    new_count = 0
    hist = account.get("history_id")
    if not hist:
        for label in ["INBOX", "SENT", "DRAFT", "TRASH"]:
            for mid in await _gmail_list_ids(account, label, 30):
                msg = await _gmail_get_message(account, mid)
                if msg:
                    await _upsert_email(uid, msg)
        profile = await _gmail_profile(account)
        if profile.get("historyId"):
            await db.gmail_accounts.update_one({"id": account["id"]}, {"$set": {"history_id": str(profile["historyId"])}})
        return 0  # never notify on the first full sync
    resp = await _gmail_request(account, "GET", "/history", params={
        "startHistoryId": hist, "historyTypes": ["messageAdded", "labelAdded", "labelRemoved"], "maxResults": 500})
    if resp.status_code == 404:
        # history too old — reset and do a full resync next time
        await db.gmail_accounts.update_one({"id": account["id"]}, {"$set": {"history_id": None}})
        return 0
    if resp.status_code >= 400:
        return 0
    data = resp.json()
    touched = set()
    for h in data.get("history", []):
        for key in ("messagesAdded", "labelsAdded", "labelsRemoved", "messages"):
            for item in h.get(key, []):
                mid = (item.get("message") or item).get("id")
                if mid:
                    touched.add(mid)
    for mid in touched:
        msg = await _gmail_get_message(account, mid)
        if not msg:
            continue
        existing = await db.emails.find_one({"uid": uid, "providerMessageId": mid}, {"_id": 0, "id": 1})
        doc = await _upsert_email(uid, msg)
        if not existing and doc["folder"] == "inbox" and doc["unread"] and not doc["outgoing"]:
            new_count += 1
            if notify:
                await _notify_new_email(uid, doc["subject"], doc["sender"], doc["threadId"], doc["providerMessageId"])
    if data.get("historyId"):
        await db.gmail_accounts.update_one({"id": account["id"]}, {"$set": {"history_id": str(data["historyId"])}})
    return new_count


# ---- Gmail send / modify helpers ----
def _build_raw(from_addr: str, body: "ComposeIn", in_reply_to: str = "", references: str = "") -> str:
    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = body.to
    if body.cc:
        msg["Cc"] = body.cc
    if body.bcc:
        msg["Bcc"] = body.bcc
    msg["Subject"] = body.subject or "(no subject)"
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
        msg["References"] = (references or in_reply_to)
    msg.set_content(body.body or "")
    for att in (body.attachments or []):
        raw = att.get("data") or ""
        if "," in raw and raw.strip().startswith("data:"):
            raw = raw.split(",", 1)[1]
        try:
            blob = base64.b64decode(raw)
        except Exception:
            continue
        mime = att.get("type") or "application/octet-stream"
        maintype, _, subtype = mime.partition("/")
        msg.add_attachment(blob, maintype=maintype or "application", subtype=subtype or "octet-stream",
                           filename=att.get("name", "attachment"))
    return base64.urlsafe_b64encode(msg.as_bytes()).decode()


async def _gmail_send_raw(account: dict, raw: str, thread_id: Optional[str]) -> dict:
    payload = {"raw": raw}
    if thread_id:
        payload["threadId"] = thread_id
    resp = await _gmail_request(account, "POST", "/messages/send", json=payload)
    if resp.status_code >= 400:
        logger.warning("Gmail send failed %s: %s", resp.status_code, resp.text[:200])
        raise HTTPException(502, "Your email could not be sent through Gmail. Please try again.")
    return resp.json()


async def _gmail_modify(account: dict, message_id: str, add: list = None, remove: list = None) -> None:
    await _gmail_request(account, "POST", f"/messages/{message_id}/modify",
                         json={"addLabelIds": add or [], "removeLabelIds": remove or []})


async def _primary_account(uid: str) -> Optional[dict]:
    acct = await db.gmail_accounts.find_one({"uid": uid}, {"_id": 0})
    if acct and not acct.get("revoked"):
        return acct
    return None


@api.get("/auth/google/login-url")
async def google_login_url():
    """Public: start the Sign in + Connect Gmail flow in a single OAuth grant."""
    if not _google_ready():
        raise HTTPException(503, "Google sign-in is not configured for this Fmail project.")
    state = secrets.token_urlsafe(32)
    await db.oauth_states.insert_one({"state": state, "uid": None, "purpose": "login",
                                      "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()})
    params = {"client_id": GOOGLE_CLIENT_ID, "redirect_uri": GOOGLE_REDIRECT_URI, "response_type": "code",
              "access_type": "offline", "prompt": "consent", "include_granted_scopes": "true",
              "scope": GMAIL_SCOPE, "state": state}
    return {"url": "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)}


@api.post("/auth/google/exchange")
async def google_exchange(body: dict):
    """Public: trade the one-time code from the login redirect for a Fmail session."""
    code = (body or {}).get("code")
    rec = await db.auth_codes.find_one({"code": code}) if code else None
    if rec:
        await db.auth_codes.delete_one({"code": code})
    if not rec or datetime.now(timezone.utc) > datetime.fromisoformat(rec["expires_at"]):
        raise HTTPException(400, "This sign-in link has expired. Please try again.")
    user = await db.users.find_one({"id": rec["uid"]}, {"_id": 0, "password": 0})
    if not user:
        raise HTTPException(404, "Account not found.")
    acct = await db.gmail_accounts.find_one({"uid": user["id"]}, {"_id": 0, "email": 1})
    user["gmailConnected"] = bool(acct)
    user["gmailEmail"] = acct["email"] if acct else None
    return {"token": make_token(user["id"]), "user": user}


@api.get("/auth/google/authorize")
async def google_authorize(user: dict = Depends(current_user)):
    """Authenticated: connect/refresh Gmail for the signed-in Fmail account."""
    if not _google_ready():
        raise HTTPException(503, "Google integration is not configured for this Fmail project.")
    state = secrets.token_urlsafe(32)
    await db.oauth_states.insert_one({"state": state, "uid": user["id"], "purpose": "connect",
                                      "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()})
    params = {"client_id": GOOGLE_CLIENT_ID, "redirect_uri": GOOGLE_REDIRECT_URI, "response_type": "code",
              "access_type": "offline", "prompt": "consent", "include_granted_scopes": "true",
              "scope": GMAIL_SCOPE, "state": state}
    return {"url": "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)}


@api.get("/auth/google/callback")
async def google_callback(code: Optional[str] = None, state: Optional[str] = None, error: Optional[str] = None):
    if error or not code or not state:
        return _app_redirect("gmail", error="cancelled")
    saved = await db.oauth_states.find_one({"state": state})
    await db.oauth_states.delete_one({"state": state})
    if not saved or datetime.now(timezone.utc) > datetime.fromisoformat(saved["expires_at"]):
        return _app_redirect("gmail", error="expired")
    purpose = saved.get("purpose", "connect")
    try:
        tokens = await _google_tokens(code)
        info = await _google_userinfo(tokens["access_token"])
        if not info.get("email") or info.get("email_verified") not in (True, "true"):
            return _app_redirect("gmail", error="unverified")
        email = info["email"].lower()
        if purpose == "login":
            uid_user = await db.users.find_one({"email": email})
            if not uid_user:
                uid = new_id()
                uid_user = {
                    "id": uid, "email": email,
                    "password": bcrypt.hashpw(secrets.token_urlsafe(32).encode(), bcrypt.gensalt()).decode(),
                    "name": info.get("name") or email.split("@", 1)[0], "photo": info.get("picture"),
                    "signature": "Sent with Fmail", "aliases": [],
                    "connectedAccounts": [{"provider": "gmail", "email": email, "connected": True}],
                    "permissions": {"notifications": True, "camera": False, "microphone": False, "contacts": False, "storage": False},
                    "aiEnabled": True, "memoryEnabled": True, "darkMode": "system", "created_at": now_iso(),
                }
                await db.users.insert_one(uid_user)
                await audit(uid, "Account created via Google", email)
            else:
                uid = uid_user["id"]
            await _store_gmail_account(uid, info, tokens)
            one_time = secrets.token_urlsafe(32)
            await db.auth_codes.insert_one({"code": one_time, "uid": uid,
                                            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()})
            return _app_redirect("auth", code=one_time)
        # connect for an already signed-in account
        await _store_gmail_account(saved["uid"], info, tokens)
        await audit(saved["uid"], "Gmail connected", email)
        return _app_redirect("gmail", connected="1")
    except HTTPException:
        return _app_redirect("gmail", error="failed")
    except Exception as exc:
        logger.warning("Google callback failed: %s", type(exc).__name__)
        return _app_redirect("gmail", error="failed")


@api.post("/auth/google/connect")
async def google_connect(body: GoogleConnectIn, user: dict = Depends(current_user)):
    tokens = await _google_tokens(body.code)
    info = await _google_userinfo(tokens["access_token"])
    if not info.get("email") or not info.get("email_verified"):
        raise HTTPException(400, "The Google account email must be verified.")
    account = await _store_gmail_account(user["id"], info, tokens)
    await audit(user["id"], "Gmail connected", account["email"])
    return {"connected": True, "email": account["email"]}


@api.post("/auth/google/disconnect")
async def google_disconnect(user: dict = Depends(current_user)):
    await db.gmail_accounts.delete_many({"uid": user["id"]})
    await db.emails.delete_many({"uid": user["id"], "account": "gmail"})
    await db.users.update_one({"id": user["id"]}, {"$set": {"connectedAccounts": [{"provider": "gmail", "email": "", "connected": False}]}})
    await audit(user["id"], "Gmail disconnected", user["email"])
    return {"connected": False}


@api.post("/push/register")
async def register_push(body: PushTokenIn, user: dict = Depends(current_user)):
    await db.push_tokens.update_one({"uid": user["id"], "token": body.token}, {"$set": {"uid": user["id"], "token": body.token, "platform": body.platform, "updated_at": now_iso()}}, upsert=True)
    return {"registered": True}


@api.delete("/push/register/{token}")
async def unregister_push(token: str, user: dict = Depends(current_user)):
    await db.push_tokens.delete_one({"uid": user["id"], "token": token})
    return {"registered": False}


async def _firebase_access_token() -> Optional[str]:
    if not FIREBASE_SERVICE_ACCOUNT_JSON:
        return None
    try:
        raw = FIREBASE_SERVICE_ACCOUNT_JSON
        if os.path.exists(raw):
            raw = Path(raw).read_text()
        service = json.loads(raw)
        issued = int(datetime.now(timezone.utc).timestamp())
        assertion = jwt.encode({"iss": service["client_email"], "scope": "https://www.googleapis.com/auth/firebase.messaging", "aud": "https://oauth2.googleapis.com/token", "iat": issued, "exp": issued + 3600}, service["private_key"], algorithm="RS256")
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post("https://oauth2.googleapis.com/token", data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": assertion})
        if response.status_code >= 400:
            logger.warning("Firebase token exchange failed with status %s", response.status_code)
            return None
        return response.json().get("access_token")
    except Exception as exc:
        logger.warning("Firebase messaging configuration unavailable: %s", type(exc).__name__)
        return None


async def _notify_new_email(uid: str, subject: str, sender: str, thread_id: str = "", message_id: str = "") -> None:
    access = await _firebase_access_token()
    if not access:
        return
    tokens = await db.push_tokens.find({"uid": uid}, {"_id": 0, "token": 1}).to_list(100)
    data = {"type": "new_email", "threadId": thread_id or "", "messageId": message_id or ""}
    async with httpx.AsyncClient(timeout=20) as client:
        for row in tokens:
            response = await client.post(
                f"https://fcm.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/messages:send",
                headers={"Authorization": f"Bearer {access}", "Content-Type": "application/json"},
                json={"message": {
                    "token": row["token"],
                    "notification": {"title": sender or "New email", "body": subject or "You received a new email"},
                    "data": data,
                    "android": {"priority": "high", "notification": {"channel_id": "fmail_mail", "click_action": "OPEN_THREAD"}},
                    "apns": {"payload": {"aps": {"sound": "default", "category": "OPEN_THREAD"}}},
                }})
            if response.status_code in (404, 410):
                await db.push_tokens.delete_one({"uid": uid, "token": row["token"]})


@api.post("/gmail/sync")
async def gmail_sync(user: dict = Depends(current_user)):
    accounts = await db.gmail_accounts.find({"uid": user["id"], "revoked": {"$ne": True}}, {"_id": 0}).to_list(20)
    if not accounts:
        raise HTTPException(400, "Connect a Google account before syncing Gmail.")
    imported = 0
    for account in accounts:
        imported += await _sync_gmail_account(account, notify=True)
    await audit(user["id"], "Gmail synchronized", f"{imported} new email(s)")
    return {"imported": imported, "ok": True}


@api.get("/gmail/status")
async def gmail_status(user: dict = Depends(current_user)):
    acct = await db.gmail_accounts.find_one({"uid": user["id"]}, {"_id": 0, "email": 1, "revoked": 1, "history_id": 1})
    return {"connected": bool(acct) and not (acct or {}).get("revoked", False),
            "email": (acct or {}).get("email"), "needsReconnect": bool(acct) and (acct or {}).get("revoked", False)}


@api.post("/gmail/watch")
async def gmail_watch(user: dict = Depends(current_user)):
    """Register Gmail push via Cloud Pub/Sub (requires GMAIL_PUBSUB_TOPIC configured in GCP)."""
    topic = os.environ.get("GMAIL_PUBSUB_TOPIC")
    if not topic:
        raise HTTPException(503, "Real-time Gmail push is not configured. Server-side polling is active instead.")
    account = await _primary_account(user["id"])
    if not account:
        raise HTTPException(400, "Connect a Google account first.")
    resp = await _gmail_request(account, "POST", "/watch", json={"topicName": topic, "labelIds": ["INBOX"]})
    if resp.status_code >= 400:
        raise HTTPException(502, "Could not enable Gmail push notifications.")
    data = resp.json()
    await db.gmail_accounts.update_one({"id": account["id"]}, {"$set": {"watch_expiration": data.get("expiration"), "history_id": str(data.get("historyId"))}})
    return {"watching": True, "expiration": data.get("expiration")}


@api.post("/gmail/push")
async def gmail_push(request: Request):
    """Public webhook for Google Cloud Pub/Sub push of Gmail changes."""
    token_q = request.query_params.get("token")
    expected = os.environ.get("GMAIL_PUSH_TOKEN")
    if expected and token_q != expected:
        raise HTTPException(403, "Invalid push token.")
    try:
        envelope = await request.json()
        raw = envelope.get("message", {}).get("data", "")
        decoded = json.loads(_b64url_decode(raw).decode("utf-8")) if raw else {}
        email = (decoded.get("emailAddress") or "").lower()
    except Exception:
        return {"ok": True}
    if email:
        account = await db.gmail_accounts.find_one({"email": email, "revoked": {"$ne": True}}, {"_id": 0})
        if account:
            try:
                await _sync_gmail_account(account, notify=True)
            except Exception as exc:
                logger.warning("Pub/Sub sync failed: %s", type(exc).__name__)
    return {"ok": True}


@api.post("/analytics")
async def analytics(body: AnalyticsEventIn, user: dict = Depends(current_user)):
    safe_params = {k: str(v)[:120] for k, v in body.params.items() if k.lower() not in {"email", "body", "content", "message", "token"}}
    await db.analytics.insert_one({"uid": user["id"], "name": body.name, "params": safe_params, "created_at": now_iso()})
    return {"recorded": True}


@api.post("/feedback")
async def feedback(body: FeedbackIn, user: dict = Depends(current_user)):
    if not RESEND_API_KEY or not RESEND_FROM_EMAIL:
        raise HTTPException(503, "Feedback delivery is temporarily unavailable. Please try again later.")
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post("https://api.resend.com/emails", headers={"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"}, json={"from": RESEND_FROM_EMAIL, "to": ["jarvisai9077@gmail.com"], "reply_to": [user["email"]], "subject": f"Fmail feedback: {body.category}", "text": f"From account: {user['email']}\nCategory: {body.category}\n\n{body.message}"})
        if response.status_code >= 400:
            raise HTTPException(503, "We could not send feedback. Please try again later.")
    except HTTPException:
        raise
    except httpx.RequestError:
        raise HTTPException(503, "Feedback delivery is temporarily unavailable. Please try again later.")
    await audit(user["id"], "Feedback sent", body.category)
    return {"sent": True}


# ----------------------------- email routes -----------------------------------
@api.get("/emails")
async def list_emails(folder: str = "inbox", filter: Optional[str] = None,
                      account: Optional[str] = None, category: Optional[str] = None,
                      space: Optional[str] = None, user: dict = Depends(current_user)):
    q: dict = {"uid": user["id"]}
    if folder in ("inbox", "sent", "drafts", "archive", "trash"):
        q["folder"] = folder
    elif folder == "important":
        q["important"] = True; q["folder"] = {"$nin": ["trash", "archive"]}
    elif folder == "starred":
        q["star"] = True; q["folder"] = {"$nin": ["trash"]}
    if filter == "unread":
        q["unread"] = True
    elif filter == "important":
        q["important"] = True
    if account:
        q["account"] = account
    if category:
        q["category"] = category
    if space:
        q["space"] = space
    docs = await db.emails.find(q, {"_id": 0}).sort("created_at", -1).to_list(500)
    # collapse to latest per thread
    seen = {}
    for d in docs:
        if d["threadId"] not in seen:
            seen[d["threadId"]] = d
    return list(seen.values())


@api.get("/threads/{tid}")
async def get_thread(tid: str, user: dict = Depends(current_user)):
    msgs = await db.emails.find({"uid": user["id"], "threadId": tid}, {"_id": 0}).sort("created_at", 1).to_list(200)
    if not msgs:
        raise HTTPException(404, "Thread not found")
    await db.emails.update_many({"uid": user["id"], "threadId": tid}, {"$set": {"unread": False}})
    # Mark read in Gmail too.
    account = await _primary_account(user["id"])
    if account:
        for m in msgs:
            if m.get("providerMessageId") and m.get("unread"):
                try:
                    await _gmail_modify(account, m["providerMessageId"], remove=["UNREAD"])
                except Exception:
                    pass
    return {"threadId": tid, "subject": msgs[0]["subject"], "messages": msgs}


@api.get("/emails/{mid}/attachment/{attachment_id}")
async def get_attachment(mid: str, attachment_id: str, user: dict = Depends(current_user)):
    """Fetch an attachment's base64 content from Gmail on demand."""
    email = await db.emails.find_one({"uid": user["id"], "providerMessageId": mid}, {"_id": 0})
    account = await _primary_account(user["id"])
    if not email or not account:
        raise HTTPException(404, "Attachment is no longer available.")
    resp = await _gmail_request(account, "GET", f"/messages/{mid}/attachments/{attachment_id}")
    if resp.status_code >= 400:
        raise HTTPException(404, "Attachment could not be downloaded.")
    raw = resp.json().get("data", "")
    att = next((a for a in email.get("attachments", []) if a.get("attachmentId") == attachment_id), {})
    # Gmail returns base64url; convert to standard base64 for the client.
    std = base64.b64encode(_b64url_decode(raw)).decode()
    return {"name": att.get("name", "attachment"), "type": att.get("mimeType", "application/octet-stream"), "data": std}


@api.post("/emails/compose")
async def compose(body: ComposeIn, user: dict = Depends(current_user)):
    account = await _primary_account(user["id"])
    # --- Real Gmail send / draft ---
    if account:
        in_reply_to = references = ""
        thread_gmail = None
        provider_draft_id = None
        if body.threadId:
            last = await db.emails.find({"uid": user["id"], "threadId": body.threadId}, {"_id": 0}).sort("created_at", -1).to_list(1)
            if last:
                in_reply_to = last[0].get("messageIdHeader", "")
                references = last[0].get("references", "") or in_reply_to
                thread_gmail = last[0].get("threadId")
        if body.draftId:
            old = await db.emails.find_one({"uid": user["id"], "id": body.draftId}, {"_id": 0})
            if old:
                provider_draft_id = old.get("providerDraftId")
                thread_gmail = thread_gmail or old.get("threadId")
        raw = _build_raw(account["email"], body, in_reply_to, references)
        if body.draft:
            payload = {"message": {"raw": raw}}
            if thread_gmail:
                payload["message"]["threadId"] = thread_gmail
            if provider_draft_id:
                resp = await _gmail_request(account, "PUT", f"/drafts/{provider_draft_id}", json=payload)
            else:
                resp = await _gmail_request(account, "POST", "/drafts", json=payload)
            if resp.status_code >= 400:
                raise HTTPException(502, "Your draft could not be saved to Gmail. Please try again.")
            draft = resp.json()
            msg = await _gmail_get_message(account, draft["message"]["id"])
            if body.draftId:
                await db.emails.delete_one({"uid": user["id"], "id": body.draftId})
            doc = await _upsert_email(user["id"], msg) if msg else None
            if doc:
                await db.emails.update_one({"uid": user["id"], "providerMessageId": doc["providerMessageId"]},
                                           {"$set": {"providerDraftId": draft["id"]}})
                doc["providerDraftId"] = draft["id"]
            await audit(user["id"], "Draft saved", f"To {body.to}: {body.subject}")
            return doc or {"ok": True}
        # send
        sent = await _gmail_send_raw(account, raw, thread_gmail)
        if body.draftId:
            old = await db.emails.find_one({"uid": user["id"], "id": body.draftId}, {"_id": 0})
            if old and old.get("providerDraftId"):
                try:
                    await _gmail_request(account, "DELETE", f"/drafts/{old['providerDraftId']}")
                except Exception:
                    pass
            await db.emails.delete_one({"uid": user["id"], "id": body.draftId})
        msg = await _gmail_get_message(account, sent["id"])
        doc = await _upsert_email(user["id"], msg) if msg else None
        await audit(user["id"], "Email sent", f"To {body.to}: {body.subject}")
        return doc or {"ok": True, "threadId": sent.get("threadId")}
    # --- Local fallback (accounts without Gmail connected, e.g. demo) ---
    tid = body.threadId or new_id()
    if body.draftId:
        await db.emails.delete_one({"uid": user["id"], "id": body.draftId, "folder": "drafts"})
    doc = {
        "id": new_id(), "threadId": tid, "uid": user["id"], "subject": body.subject,
        "sender": user["name"], "senderEmail": _user_addr(user), "to": body.to,
        "cc": body.cc or "", "bcc": body.bcc or "", "attachments": body.attachments or [],
        "account": body.account, "category": "Work", "aiLabel": "FYI", "important": False,
        "unread": False, "star": False, "folder": "drafts" if body.draft else "sent",
        "snippet": (body.body or "")[:120], "body": body.body, "bodyHtml": "", "suspicious": False, "space": None,
        "outgoing": True, "created_at": now_iso(),
    }
    await db.emails.insert_one(doc)
    await audit(user["id"], "Draft saved" if body.draft else "Email sent", f"To {body.to}: {body.subject}")
    doc.pop("_id", None)
    return doc


@api.delete("/emails/{tid}")
async def delete_email(tid: str, user: dict = Depends(current_user)):
    """Move a thread to trash; permanently delete if already in trash. Mirrors to Gmail."""
    msgs = await db.emails.find({"uid": user["id"], "threadId": tid}, {"_id": 0}).to_list(200)
    if not msgs:
        raise HTTPException(404, "Email not found")
    account = await _primary_account(user["id"])
    already_trash = msgs[0].get("folder") == "trash"
    for m in msgs:
        pid = m.get("providerMessageId")
        if account and pid:
            try:
                if already_trash:
                    await _gmail_request(account, "DELETE", f"/messages/{pid}")
                elif m.get("providerDraftId"):
                    await _gmail_request(account, "DELETE", f"/drafts/{m['providerDraftId']}")
                else:
                    await _gmail_request(account, "POST", f"/messages/{pid}/trash")
            except Exception:
                pass
    if already_trash:
        await db.emails.delete_many({"uid": user["id"], "threadId": tid})
    else:
        await db.emails.update_many({"uid": user["id"], "threadId": tid}, {"$set": {"folder": "trash"}})
    return {"ok": True}


@api.patch("/emails/{tid}")
async def patch_email(tid: str, body: PatchEmailIn, user: dict = Depends(current_user)):
    updates = {k: v for k, v in body.dict().items() if v is not None}
    if not updates:
        return {"ok": True}
    msgs = await db.emails.find({"uid": user["id"], "threadId": tid}, {"_id": 0}).to_list(200)
    account = await _primary_account(user["id"])
    if account and msgs:
        add, remove = [], []
        if "star" in updates:
            (add if updates["star"] else remove).append("STARRED")
        if "important" in updates:
            (add if updates["important"] else remove).append("IMPORTANT")
        if "read" in updates:
            (remove if updates["read"] else add).append("UNREAD")
        if "folder" in updates and updates["folder"] == "trash":
            add.append("TRASH"); remove.append("INBOX")
        if add or remove:
            for m in msgs:
                if m.get("providerMessageId"):
                    try:
                        await _gmail_modify(account, m["providerMessageId"], add=add, remove=remove)
                    except Exception:
                        pass
    # local mirror (map read -> unread flag)
    local = dict(updates)
    if "read" in local:
        local["unread"] = not local.pop("read")
    await db.emails.update_many({"uid": user["id"], "threadId": tid}, {"$set": local})
    return {"ok": True, **updates}


# ----------------------------- AI routes --------------------------------------
@api.post("/ai/understand/{tid}")
async def ai_understand(tid: str, user: dict = Depends(current_user)):
    cached = await db.ai_cache.find_one({"uid": user["id"], "key": "understand:" + tid}, {"_id": 0})
    if cached:
        return cached["data"]
    msgs = await db.emails.find({"uid": user["id"], "threadId": tid}, {"_id": 0}).to_list(50)
    if not msgs:
        raise HTTPException(404, "Thread not found")
    m = msgs[-1]
    fallback = {
        "intent": "Requesting an action from you", "topic": m["subject"],
        "keyInfo": [m["snippet"]], "requestedAction": "Review and respond",
        "deadline": "Not specified", "people": [m["sender"]], "company": "", "project": "",
        "questions": [], "commitments": [], "followUp": True,
    }
    data = await llm_json(
        "You are Fmail's email understanding engine. Extract structured intelligence from an email.",
        f"Email from {m['sender']} <{m['senderEmail']}>\nSubject: {m['subject']}\nBody:\n{m['body']}\n\n"
        'Return JSON with keys: intent (string), topic (string), keyInfo (array of strings), '
        'requestedAction (string), deadline (string), people (array), company (string), project (string), '
        'questions (array), commitments (array), followUp (boolean).', fallback)
    await db.ai_cache.insert_one({"uid": user["id"], "key": "understand:" + tid, "data": data})
    await audit(user["id"], "AI analyzed email", m["subject"], actor="Fmail AI")
    return data


@api.post("/ai/thread/{tid}")
async def ai_thread(tid: str, user: dict = Depends(current_user)):
    cached = await db.ai_cache.find_one({"uid": user["id"], "key": "thread:" + tid}, {"_id": 0})
    if cached:
        return cached["data"]
    msgs = await db.emails.find({"uid": user["id"], "threadId": tid}, {"_id": 0}).sort("created_at", 1).to_list(50)
    if not msgs:
        raise HTTPException(404, "Thread not found")
    convo = "\n\n".join([f"{x['sender']}: {x['body']}" for x in msgs])
    fallback = {
        "summary": msgs[-1]["snippet"], "timeline": [f"{x['sender']} wrote about {msgs[0]['subject']}" for x in msgs],
        "decisions": [], "openQuestions": [], "pendingActions": ["Respond to latest message"],
        "participants": list({x["sender"] for x in msgs}), "latestStatus": "Awaiting your reply",
        "nextAction": "Draft a reply",
    }
    data = await llm_json(
        "You are Fmail's thread understanding engine.",
        f"Email thread:\n{convo}\n\nReturn JSON: summary (string), timeline (array of strings), "
        "decisions (array), openQuestions (array), pendingActions (array), participants (array), "
        "latestStatus (string), nextAction (string).", fallback)
    await db.ai_cache.insert_one({"uid": user["id"], "key": "thread:" + tid, "data": data})
    return data


@api.post("/ai/reply")
async def ai_reply(body: ReplyIn, user: dict = Depends(current_user)):
    msgs = await db.emails.find({"uid": user["id"], "threadId": body.threadId}, {"_id": 0}).sort("created_at", 1).to_list(50)
    context = "\n\n".join([f"{x['sender']}: {x['body']}" for x in msgs]) if msgs else ""
    action_map = {
        "reply": f"Write a {body.tone.lower()} reply to the latest email.",
        "rewrite": "Rewrite the following draft to improve clarity.",
        "shorten": "Make the following draft shorter and more concise.",
        "expand": "Expand the following draft with more detail.",
        "grammar": "Fix grammar and spelling in the following draft, keep the meaning.",
        "translate": "Translate the following draft to Hindi.",
        "professional": "Make the following draft more professional.",
    }
    instr = action_map.get(body.action, action_map["reply"])
    prompt = (f"{instr}\nTone: {body.tone}.\n"
              + (f"Draft:\n{body.draft}\n" if body.draft else "")
              + (f"Email context:\n{context}\n" if context else "")
              + f"Sign as {user['name']}. Return only the email text, no preamble.")
    fallback = f"Hi,\n\nThanks for your email. I'll get back to you shortly.\n\nBest,\n{user['name']}"
    text = await llm_text("You are Fmail's AI reply writer.", prompt, fallback)
    await audit(user["id"], "AI drafted reply", body.action, actor="Fmail AI")
    return {"text": text}


TONES = ["Professional", "Friendly", "Short", "Detailed", "Formal", "Casual", "Direct", "Diplomatic"]


@api.post("/ai/compose")
async def ai_compose(body: AiComposeIn, user: dict = Depends(current_user)):
    """Generate a full email (subject + body) from a plain-language instruction and tone."""
    tone = body.tone if body.tone in TONES else "Professional"
    tone_hint = {
        "Professional": "clear, polished and businesslike",
        "Friendly": "warm, approachable and personable",
        "Short": "very concise, a few sentences at most",
        "Detailed": "thorough, well-structured with all relevant detail",
        "Formal": "formal, respectful and traditional",
        "Casual": "relaxed, conversational and informal",
        "Direct": "straight to the point, no filler",
        "Diplomatic": "tactful, considerate and balanced",
    }[tone]
    prompt = (
        f"Write an email based on this instruction: {body.instruction}\n"
        + (f"Recipient: {body.to}\n" if body.to else "")
        + (f"Additional context:\n{body.context}\n" if body.context else "")
        + f"Style: {tone_hint}.\n"
        f"Sign the email as {user['name']}.\n"
        'Return ONLY minified JSON: {"subject": string, "body": string}. No markdown.'
    )
    fallback = {
        "subject": (body.instruction[:60] or "Message from " + user["name"]),
        "body": f"Hi,\n\n{body.instruction}\n\nBest,\n{user['name']}",
    }
    data = await llm_json("You are Fmail's AI email writer. You draft complete, ready-to-edit emails.", prompt, fallback)
    await audit(user["id"], "AI drafted email", tone, actor="Fmail AI")
    return {"subject": data.get("subject", fallback["subject"]), "body": data.get("body", fallback["body"])}


@api.post("/ai/ask")
async def ai_ask(body: AskIn, user: dict = Depends(current_user)):
    uid = user["id"]
    emails = await db.emails.find({"uid": uid, "folder": "inbox"}, {"_id": 0}).sort("created_at", -1).to_list(30)
    tasks = await db.tasks.find({"uid": uid}, {"_id": 0}).to_list(30)
    events = await db.events.find({"uid": uid}, {"_id": 0}).to_list(30)
    meetings = await db.meetings.find({"uid": uid}, {"_id": 0}).to_list(10)
    memory = await db.memory.find({"uid": uid}, {"_id": 0}).to_list(30)
    ctx = "EMAILS:\n" + "\n".join([f"- [{e['aiLabel']}] {e['sender']}: {e['subject']} — {e['snippet']}" for e in emails])
    ctx += "\n\nTASKS:\n" + "\n".join([f"- {t['title']} (due {t.get('due','?')}, {t['priority']})" for t in tasks])
    ctx += "\n\nCALENDAR:\n" + "\n".join([f"- {ev['title']} at {ev['start']}" for ev in events])
    ctx += "\n\nMEETINGS:\n" + "\n".join([f"- {m['title']}: {m.get('notes',{}).get('summary','') if isinstance(m.get('notes'),dict) else ''}" for m in meetings])
    ctx += "\n\nMEMORY:\n" + "\n".join([f"- [{m['kind']}] {m['title']}: {m['detail']}" for m in memory])
    fallback = "I looked across your inbox, tasks and calendar. You have urgent items like the client proposal (due Friday) and invoice #INV-2043. Enable AI to get full natural-language answers."
    answer = await llm_text(
        "You are Ask Fmail, a personal communication chief of staff. Answer concisely using ONLY the provided context. "
        "Use short paragraphs or bullet points. If unknown, say so.",
        f"Context about the user's communication world:\n{ctx}\n\nQuestion: {body.question}", fallback)
    await db.ai_chat.insert_one({"id": new_id(), "uid": uid, "q": body.question, "a": answer, "created_at": now_iso()})
    await audit(uid, "Asked Fmail AI", body.question[:60], actor="You")
    return {"answer": answer}


@api.get("/ai/chat-history")
async def chat_history(user: dict = Depends(current_user)):
    docs = await db.ai_chat.find({"uid": user["id"]}, {"_id": 0}).sort("created_at", 1).to_list(100)
    return docs


@api.post("/ai/email-to-task/{tid}")
async def email_to_task(tid: str, user: dict = Depends(current_user)):
    msgs = await db.emails.find({"uid": user["id"], "threadId": tid}, {"_id": 0}).to_list(10)
    if not msgs:
        raise HTTPException(404, "Thread not found")
    m = msgs[-1]
    fallback = {"title": f"Follow up: {m['subject']}", "due": None, "priority": "medium"}
    data = await llm_json(
        "Extract a single actionable task from this email.",
        f"Email: {m['subject']}\n{m['body']}\nReturn JSON: title (string), due (ISO date or null), priority (low|medium|high).",
        fallback)
    task = {"id": new_id(), "uid": user["id"], "title": data.get("title", fallback["title"]),
            "due": data.get("due"), "priority": data.get("priority", "medium"), "labels": [m["category"]],
            "project": None, "notes": None, "subtasks": [], "done": False,
            "source": f"Email: {m['subject']}", "created_at": now_iso()}
    await db.tasks.insert_one(task)
    await audit(user["id"], "Email converted to task", task["title"], actor="Fmail AI")
    task.pop("_id", None)
    return task


@api.post("/ai/file-summary/{fid}")
async def file_summary(fid: str, user: dict = Depends(current_user)):
    f = await db.files.find_one({"uid": user["id"], "id": fid}, {"_id": 0})
    if not f:
        raise HTTPException(404, "File not found")
    summary = await llm_text(
        "You are Fmail's Attachment Brain. Produce a concise, useful summary of a document based on its name and context.",
        f"File name: {f['name']}\nType: {f['type']}\nSource: {f.get('source','')}\n"
        "Give a 2-3 sentence plausible summary and 3 key points as bullet lines.",
        f"{f['name']} is a {f['type']} document. Enable AI for a full summary and extracted key points.")
    await db.files.update_one({"id": fid}, {"$set": {"summary": summary}})
    await audit(user["id"], "AI summarized file", f["name"], actor="Fmail AI")
    return {"summary": summary}


# ----------------------------- dashboard --------------------------------------
@api.get("/dashboard")
async def dashboard(user: dict = Depends(current_user)):
    uid = user["id"]
    inbox = await db.emails.find({"uid": uid, "folder": "inbox"}, {"_id": 0}).sort("created_at", -1).to_list(200)
    seen = {}
    for e in inbox:
        seen.setdefault(e["threadId"], e)
    inbox = list(seen.values())
    urgent = [e for e in inbox if e["aiLabel"] in ("Urgent", "Action Required")]
    important = [e for e in inbox if e["important"]]
    waiting = [e for e in inbox if e["aiLabel"] == "Waiting for Reply"]
    tasks = await db.tasks.find({"uid": uid, "done": False}, {"_id": 0}).to_list(50)
    events = await db.events.find({"uid": uid}, {"_id": 0}).to_list(50)
    followups = await db.followups.find({"uid": uid, "status": "open"}, {"_id": 0}).to_list(50)
    now = datetime.now(timezone.utc)
    today = [ev for ev in events if ev["start"][:10] == now.date().isoformat()]
    unread = len([e for e in inbox if e["unread"]])
    brief = (f"Good day, {user['name'].split()[0]}. You have {len(urgent)} urgent email"
             f"{'s' if len(urgent)!=1 else ''}, {len(today)} meeting{'s' if len(today)!=1 else ''} today, "
             f"{len(waiting)+len(followups)} pending repl{'ies' if (len(waiting)+len(followups))!=1 else 'y'} "
             f"and {len(tasks)} open task{'s' if len(tasks)!=1 else ''}.")
    return {
        "brief": brief, "unread": unread,
        "important": important[:5], "needsAction": urgent[:5], "waitingFor": waiting[:5],
        "todayMeetings": events[:4], "tasks": tasks[:5], "followups": followups[:5],
        "counts": {"urgent": len(urgent), "important": len(important), "waiting": len(waiting) + len(followups),
                   "tasks": len(tasks), "meetings": len(events)},
    }


# ----------------------------- generic CRUD -----------------------------------
async def _upsert(coll, uid, data: dict, extra: dict = None):
    data = {k: v for k, v in data.items() if v is not None}
    if data.get("id"):
        oid = data.pop("id")
        await db[coll].update_one({"uid": uid, "id": oid}, {"$set": data})
        return await db[coll].find_one({"uid": uid, "id": oid}, {"_id": 0})
    doc = {"id": new_id(), "uid": uid, **(extra or {}), **data, "created_at": now_iso()}
    await db[coll].insert_one(doc)
    doc.pop("_id", None)
    return doc


@api.get("/tasks")
async def get_tasks(user: dict = Depends(current_user)):
    return await db.tasks.find({"uid": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(300)


@api.post("/tasks")
async def save_task(body: TaskIn, user: dict = Depends(current_user)):
    return await _upsert("tasks", user["id"], body.dict())


@api.delete("/tasks/{tid}")
async def del_task(tid: str, user: dict = Depends(current_user)):
    await db.tasks.delete_one({"uid": user["id"], "id": tid})
    return {"ok": True}


@api.get("/events")
async def get_events(user: dict = Depends(current_user)):
    return await db.events.find({"uid": user["id"]}, {"_id": 0}).sort("start", 1).to_list(300)


@api.post("/events")
async def save_event(body: EventIn, user: dict = Depends(current_user)):
    return await _upsert("events", user["id"], body.dict())


@api.delete("/events/{eid}")
async def del_event(eid: str, user: dict = Depends(current_user)):
    await db.events.delete_one({"uid": user["id"], "id": eid})
    return {"ok": True}


@api.get("/contacts")
async def get_contacts(user: dict = Depends(current_user)):
    return await db.contacts.find({"uid": user["id"]}, {"_id": 0}).sort("name", 1).to_list(500)


@api.post("/contacts")
async def save_contact(body: ContactIn, user: dict = Depends(current_user)):
    return await _upsert("contacts", user["id"], body.dict())


@api.get("/contacts/{cid}/graph")
async def contact_graph(cid: str, user: dict = Depends(current_user)):
    c = await db.contacts.find_one({"uid": user["id"], "id": cid}, {"_id": 0})
    if not c:
        raise HTTPException(404, "Contact not found")
    emails = await db.emails.find({"uid": user["id"], "senderEmail": c["email"]}, {"_id": 0}).to_list(50)
    meetings = await db.meetings.find({"uid": user["id"], "attendees": c["email"]}, {"_id": 0}).to_list(50)
    tasks = await db.tasks.find({"uid": user["id"], "project": c.get("company")}, {"_id": 0}).to_list(50)
    memory = await db.memory.find({"uid": user["id"], "title": c["name"]}, {"_id": 0}).to_list(20)
    return {"contact": c, "emails": emails, "meetings": meetings, "tasks": tasks, "memory": memory}


@api.get("/files")
async def get_files(user: dict = Depends(current_user)):
    return await db.files.find({"uid": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(300)


@api.post("/files")
async def save_file(name: str = Form(...), type: str = Form("document"),
                    size: str = Form(""), data: Optional[str] = Form(None), user: dict = Depends(current_user)):
    if data and len(data) > 12 * 1024 * 1024:
        raise HTTPException(413, "This file is too large. Please choose a file under 8 MB.")
    if data and not re.match(r"^[A-Za-z0-9+/=]+$", data):
        raise HTTPException(400, "The selected file could not be read. Please try again.")
    return await _upsert("files", user["id"], {"name": name, "type": type, "size": size, "data": data, "summary": None, "source": "Uploaded"})


@api.get("/files/{fid}/download")
async def download_file(fid: str, user: dict = Depends(current_user)):
    doc = await db.files.find_one({"uid": user["id"], "id": fid}, {"_id": 0})
    if not doc or not doc.get("data"):
        raise HTTPException(404, "File content is no longer available.")
    return {"name": doc["name"], "type": doc.get("mimeType", "application/octet-stream"), "data": doc["data"]}



@api.get("/memory")
async def get_memory(kind: Optional[str] = None, user: dict = Depends(current_user)):
    q = {"uid": user["id"]}
    if kind:
        q["kind"] = kind
    return await db.memory.find(q, {"_id": 0}).sort("created_at", -1).to_list(500)


@api.post("/memory")
async def save_memory(body: MemoryIn, user: dict = Depends(current_user)):
    return await _upsert("memory", user["id"], body.dict())


@api.delete("/memory/{mid}")
async def del_memory(mid: str, user: dict = Depends(current_user)):
    await db.memory.delete_one({"uid": user["id"], "id": mid})
    return {"ok": True}


@api.get("/spaces")
async def get_spaces(user: dict = Depends(current_user)):
    return await db.spaces.find({"uid": user["id"]}, {"_id": 0}).to_list(100)


@api.post("/spaces")
async def save_space(body: SpaceIn, user: dict = Depends(current_user)):
    return await _upsert("spaces", user["id"], body.dict())


@api.get("/decisions")
async def get_decisions(user: dict = Depends(current_user)):
    return await db.decisions.find({"uid": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)


@api.get("/commitments")
async def get_commitments(user: dict = Depends(current_user)):
    return await db.commitments.find({"uid": user["id"]}, {"_id": 0}).to_list(200)


@api.get("/followups")
async def get_followups(user: dict = Depends(current_user)):
    return await db.followups.find({"uid": user["id"]}, {"_id": 0}).to_list(200)


@api.post("/followups/{fid}/{act}")
async def act_followup(fid: str, act: str, user: dict = Depends(current_user)):
    await db.followups.update_one({"uid": user["id"], "id": fid}, {"$set": {"status": act}})
    await audit(user["id"], f"Follow-up {act}", fid)
    return {"ok": True}


@api.get("/audit")
async def get_audit(user: dict = Depends(current_user)):
    return await db.audit.find({"uid": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)


@api.get("/notifications")
async def get_notifications(user: dict = Depends(current_user)):
    return await db.notifications.find({"uid": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(100)


# ----------------------------- meetings ---------------------------------------
@api.get("/meetings")
async def get_meetings(user: dict = Depends(current_user)):
    return await db.meetings.find({"uid": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)


@api.get("/meetings/{mid}")
async def get_meeting(mid: str, user: dict = Depends(current_user)):
    m = await db.meetings.find_one({"uid": user["id"], "id": mid}, {"_id": 0})
    if not m:
        raise HTTPException(404, "Meeting not found")
    return m


@api.post("/meetings")
async def save_meeting(body: MeetingIn, user: dict = Depends(current_user)):
    data = body.dict()
    if not data.get("id"):
        data.update({"status": "active", "transcript": [], "notes": None,
                     "start": data.get("start") or now_iso()})
    doc = await _upsert("meetings", user["id"], data)
    await audit(user["id"], "Meeting started", body.title)
    return doc


@api.post("/meetings/{mid}/share")
async def share_meeting(mid: str, user: dict = Depends(current_user)):
    meeting = await db.meetings.find_one({"uid": user["id"], "id": mid}, {"_id": 0, "id": 1, "title": 1})
    if not meeting:
        raise HTTPException(404, "Meeting not found")
    base = os.environ.get("APP_URL")
    if not base:
        raise HTTPException(503, "Meeting sharing is not configured.")
    return {"url": base.rstrip("/") + "/meeting/" + mid, "title": meeting.get("title", "Fmail meeting")}


@api.post("/meetings/{mid}/notes")
async def generate_notes(mid: str, user: dict = Depends(current_user)):
    m = await db.meetings.find_one({"uid": user["id"], "id": mid}, {"_id": 0})
    if not m:
        raise HTTPException(404, "Meeting not found")
    transcript = "\n".join([f"{x['speaker']}: {x['text']}" for x in m.get("transcript", [])])
    fallback = {
        "summary": "The meeting covered the main agenda items and next steps.",
        "keyPoints": ["Discussed the agenda", "Aligned on next steps"],
        "decisions": [], "actionItems": [], "questions": [], "nextSteps": ["Follow up over email"],
    }
    notes = await llm_json(
        "You are Fmail's AI Meeting Copilot. Generate meeting minutes from a transcript.",
        f"Meeting: {m['title']} (mode: {m.get('mode')})\nTranscript:\n{transcript}\n\n"
        "Return JSON: summary (string), keyPoints (array), decisions (array), actionItems (array), "
        "questions (array), nextSteps (array).", fallback)
    await db.meetings.update_one({"id": mid}, {"$set": {"notes": notes, "status": "completed"}})
    await audit(user["id"], "AI generated meeting notes", m["title"], actor="Fmail AI")
    return notes


@api.post("/meetings/{mid}/ask")
async def ask_meeting(mid: str, body: AskIn, user: dict = Depends(current_user)):
    m = await db.meetings.find_one({"uid": user["id"], "id": mid}, {"_id": 0})
    if not m:
        raise HTTPException(404, "Meeting not found")
    transcript = "\n".join([f"{x['speaker']}: {x['text']}" for x in m.get("transcript", [])])
    answer = await llm_text(
        "You are Ask Meeting. Answer using ONLY the meeting transcript. Be concise.",
        f"Transcript:\n{transcript}\n\nQuestion: {body.question}",
        "I could not find that in the meeting transcript.")
    return {"answer": answer}


# ----------------------------- agents -----------------------------------------
MARKETPLACE = [
    {"name": "Job Hunter Agent", "cat": "Students", "desc": "Finds and tracks relevant job openings from your inbox.", "rating": 4.8, "installs": "45k", "dev": "Fmail", "verified": True, "perms": ["Read emails", "Create tasks"]},
    {"name": "Sales Agent", "cat": "Business", "desc": "Qualifies leads and drafts sales follow-ups.", "rating": 4.7, "installs": "32k", "dev": "Fmail", "verified": True, "perms": ["Read emails", "Create drafts"]},
    {"name": "Customer Support Agent", "cat": "Business", "desc": "Triages support emails and suggests replies.", "rating": 4.6, "installs": "28k", "dev": "Fmail", "verified": True, "perms": ["Read emails", "Create drafts"]},
    {"name": "Invoice Agent", "cat": "Finance", "desc": "Detects invoices, tracks due dates, and reminds you.", "rating": 4.9, "installs": "51k", "dev": "Fmail", "verified": True, "perms": ["Read emails", "Create reminders"]},
    {"name": "Meeting Agent", "cat": "Productivity", "desc": "Schedules meetings and prepares agendas.", "rating": 4.8, "installs": "60k", "dev": "Fmail", "verified": True, "perms": ["Read calendar", "Create calendar events"]},
    {"name": "Follow-up Agent", "cat": "Productivity", "desc": "Tracks unanswered emails and drafts follow-ups.", "rating": 4.9, "installs": "72k", "dev": "Fmail", "verified": True, "perms": ["Read emails", "Create drafts"]},
    {"name": "Task Agent", "cat": "Productivity", "desc": "Turns emails and meetings into organized tasks.", "rating": 4.7, "installs": "40k", "dev": "Fmail", "verified": True, "perms": ["Read emails", "Create tasks"]},
    {"name": "College Agent", "cat": "Students", "desc": "Tracks assignments, deadlines and campus emails.", "rating": 4.6, "installs": "22k", "dev": "Fmail", "verified": True, "perms": ["Read emails", "Create reminders"]},
    {"name": "Internship Agent", "cat": "Students", "desc": "Surfaces internship opportunities and deadlines.", "rating": 4.5, "installs": "18k", "dev": "Fmail", "verified": True, "perms": ["Read emails"]},
    {"name": "Scholarship Agent", "cat": "Students", "desc": "Finds scholarships and tracks application dates.", "rating": 4.5, "installs": "12k", "dev": "Fmail", "verified": True, "perms": ["Read emails"]},
    {"name": "Finance Agent", "cat": "Finance", "desc": "Understands bills, subscriptions and payment deadlines.", "rating": 4.8, "installs": "38k", "dev": "Fmail", "verified": True, "perms": ["Read emails", "Create reminders"]},
    {"name": "Travel Agent", "cat": "Travel", "desc": "Organizes bookings, itineraries and travel emails.", "rating": 4.6, "installs": "26k", "dev": "Fmail", "verified": True, "perms": ["Read emails", "Create calendar events"]},
    {"name": "Shopping Agent", "cat": "Shopping", "desc": "Tracks orders, deliveries and price drops.", "rating": 4.4, "installs": "30k", "dev": "Fmail", "verified": True, "perms": ["Read emails"]},
    {"name": "Developer Agent", "cat": "Developers", "desc": "Summarizes PRs, issues and deploy alerts.", "rating": 4.7, "installs": "21k", "dev": "Fmail", "verified": True, "perms": ["Read emails"]},
    {"name": "Founder Agent", "cat": "Enterprise", "desc": "Your startup chief of staff across email and meetings.", "rating": 4.9, "installs": "15k", "dev": "Fmail", "verified": True, "perms": ["Read emails", "Read calendar", "Create tasks"]},
]


@api.get("/agents/marketplace")
async def marketplace(user: dict = Depends(current_user)):
    installed = await db.agents.find({"uid": user["id"]}, {"_id": 0}).to_list(200)
    names = {a["name"] for a in installed}
    return [{**a, "installed": a["name"] in names} for a in MARKETPLACE]


@api.get("/agents/installed")
async def installed_agents(user: dict = Depends(current_user)):
    return await db.agents.find({"uid": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)


@api.post("/agents/install")
async def install_agent(body: dict, user: dict = Depends(current_user)):
    name = body.get("name")
    existing = await db.agents.find_one({"uid": user["id"], "name": name})
    if existing:
        raise HTTPException(400, "Agent already installed")
    meta = next((a for a in MARKETPLACE if a["name"] == name), None)
    doc = {"id": new_id(), "uid": user["id"], "name": name, "enabled": True, "memory": [],
           "custom": meta is None, "perms": (meta or {}).get("perms", []),
           "desc": (meta or {}).get("desc", body.get("desc", "")),
           "instructions": body.get("instructions", ""), "triggers": body.get("triggers", []),
           "created_at": now_iso()}
    await db.agents.insert_one(doc)
    await audit(user["id"], "Agent installed", name)
    doc.pop("_id", None)
    return doc


@api.post("/agents/{aid}/toggle")
async def toggle_agent(aid: str, user: dict = Depends(current_user)):
    a = await db.agents.find_one({"uid": user["id"], "id": aid})
    if not a:
        raise HTTPException(404, "Agent not found")
    await db.agents.update_one({"id": aid}, {"$set": {"enabled": not a["enabled"]}})
    return {"ok": True, "enabled": not a["enabled"]}


@api.delete("/agents/{aid}")
async def uninstall_agent(aid: str, user: dict = Depends(current_user)):
    await db.agents.delete_one({"uid": user["id"], "id": aid})
    await audit(user["id"], "Agent uninstalled", aid)
    return {"ok": True}


# ----------------------------- AI Representative ------------------------------
@api.get("/representative")
async def get_rep(user: dict = Depends(current_user)):
    rep = await db.representative.find_one({"uid": user["id"]}, {"_id": 0})
    if not rep:
        rep = {"id": new_id(), "uid": user["id"], "mode": "AI Representative", "instructions": "",
               "perms": {"read": True, "speak": True, "present": False, "files": False,
                         "negotiate": False, "decisions": False, "sending": False, "financial": False},
               "negotiationFloor": 50000, "created_at": now_iso()}
        await db.representative.insert_one(rep)
        rep.pop("_id", None)
    return rep


@api.put("/representative")
async def set_rep(body: dict, user: dict = Depends(current_user)):
    body.pop("_id", None); body.pop("id", None)
    await db.representative.update_one({"uid": user["id"]}, {"$set": body}, upsert=True)
    await audit(user["id"], "AI Representative configured", body.get("mode", ""))
    return await db.representative.find_one({"uid": user["id"]}, {"_id": 0})


# ----------------------------- Sarvam voice -----------------------------------
class SarvamError(HTTPException):
    """Maps Sarvam failures to user-friendly messages across 8 error levels."""


def _map_sarvam_status(status: int, text: str) -> SarvamError:
    snippet = (text or "")[:200]
    if status in (401, 403):
        return SarvamError(502, "Voice service authentication failed. Please contact support.")
    if status == 429:
        return SarvamError(429, "Voice service is busy right now. Please try again in a moment.")
    if status in (402, 413) or "quota" in snippet.lower() or "limit exceeded" in snippet.lower():
        return SarvamError(402, "Voice service quota reached. Please try again later.")
    if 500 <= status < 600:
        return SarvamError(502, "Voice service is temporarily unavailable. Please try again.")
    return SarvamError(502, "Voice service returned an error. Please try again.")


async def _sarvam_post(path: str, *, headers: dict, retries: int = 2, **kwargs) -> dict:
    """POST to Sarvam with retry + full 8-level error handling."""
    last_exc: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            async with httpx.AsyncClient(timeout=45) as c:
                r = await c.post("https://api.sarvam.ai" + path, headers=headers, **kwargs)
        except httpx.TimeoutException:
            last_exc = SarvamError(504, "Voice request timed out. Please check your connection and try again.")
        except httpx.TransportError:
            last_exc = SarvamError(503, "Network problem reaching the voice service. Please check your connection.")
        except Exception as e:
            logger.warning(f"sarvam unexpected {path}: {e}")
            last_exc = SarvamError(502, "Something went wrong with the voice service. Please try again.")
        else:
            if r.status_code < 400:
                try:
                    return r.json()
                except Exception:
                    raise SarvamError(502, "Voice service returned an unexpected response. Please try again.")
            logger.warning(f"sarvam {path} {r.status_code}: {r.text[:200]}")
            err = _map_sarvam_status(r.status_code, r.text)
            # only retry transient errors (429 / 5xx)
            if r.status_code not in (429,) and not (500 <= r.status_code < 600):
                raise err
            last_exc = err
        if attempt < retries:
            import asyncio
            await asyncio.sleep(0.6 * (attempt + 1))
    raise last_exc or SarvamError(502, "Voice service failed. Please try again.")


@api.post("/voice/transcribe")
async def transcribe(file: UploadFile = File(...), language_code: str = Form("hi-IN"),
                     mode: str = Form("codemix"), user: dict = Depends(current_user)):
    if not SARVAM_API_KEY:
        raise HTTPException(503, "Voice transcription is not configured.")
    data = await file.read()
    if not data:
        raise HTTPException(413, "The recording was empty. Please try again.")
    form = {"language_code": language_code, "mode": mode, "model": "saaras:v3"}
    files = {"file": (file.filename or "audio.m4a", data, file.content_type or "audio/mp4")}
    return await _sarvam_post("/speech-to-text",
                              headers={"api-subscription-key": SARVAM_API_KEY}, data=form, files=files)


@api.post("/translate")
async def translate(body: TranslateIn, user: dict = Depends(current_user)):
    if not SARVAM_API_KEY:
        raise HTTPException(503, "Translation is not configured.")
    if body.source == body.target:
        raise HTTPException(400, "Source and target languages must differ.")
    payload = {"input": body.text, "source_language_code": body.source,
               "target_language_code": body.target, "model": "mayura:v1", "mode": "modern-colloquial"}
    return await _sarvam_post("/translate",
                              headers={"api-subscription-key": SARVAM_API_KEY, "Content-Type": "application/json"},
                              json=payload)


# ----------------------------- search -----------------------------------------
@api.get("/search")
async def search(q: str, user: dict = Depends(current_user)):
    uid = user["id"]
    ql = q.lower()

    def match(text):
        return ql in (text or "").lower()

    # Pull live Gmail search results into the cache so search reflects the full mailbox.
    account = await _primary_account(uid)
    if account and q.strip():
        try:
            resp = await _gmail_request(account, "GET", "/messages", params={"q": q, "maxResults": 20})
            if resp.status_code < 400:
                for m in resp.json().get("messages", []):
                    if not await db.emails.find_one({"uid": uid, "providerMessageId": m["id"]}, {"_id": 0, "id": 1}):
                        full = await _gmail_get_message(account, m["id"])
                        if full:
                            await _upsert_email(uid, full)
        except Exception as exc:
            logger.warning("Gmail search failed: %s", type(exc).__name__)

    emails = await db.emails.find({"uid": uid}, {"_id": 0}).to_list(500)
    tasks = await db.tasks.find({"uid": uid}, {"_id": 0}).to_list(300)
    events = await db.events.find({"uid": uid}, {"_id": 0}).to_list(300)
    meetings = await db.meetings.find({"uid": uid}, {"_id": 0}).to_list(100)
    contacts = await db.contacts.find({"uid": uid}, {"_id": 0}).to_list(300)
    memory = await db.memory.find({"uid": uid}, {"_id": 0}).to_list(300)
    decisions = await db.decisions.find({"uid": uid}, {"_id": 0}).to_list(200)
    return {
        "emails": [e for e in emails if match(e.get("subject")) or match(e.get("snippet")) or match(e.get("sender")) or match(e.get("body"))][:20],
        "tasks": [t for t in tasks if match(t["title"])][:20],
        "events": [e for e in events if match(e["title"])][:20],
        "meetings": [m for m in meetings if match(m["title"])][:20],
        "contacts": [c for c in contacts if match(c["name"]) or match(c.get("company"))][:20],
        "memory": [m for m in memory if match(m["title"]) or match(m["detail"])][:20],
        "decisions": [d for d in decisions if match(d["text"])][:20],
    }


app.include_router(api)
app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])


gmail_task = None


@app.on_event("startup")
async def startup():
    global gmail_task

    async def poll():
        while True:
            try:
                accounts = await db.gmail_accounts.find({"revoked": {"$ne": True}}, {"_id": 0}).to_list(500)
                for account in accounts:
                    try:
                        await _sync_gmail_account(account, notify=True)
                    except Exception as exc:
                        logger.warning("Gmail background sync failed for %s: %s", account.get("email"), type(exc).__name__)
            except Exception as exc:
                logger.warning("Gmail background poll failed: %s", type(exc).__name__)
            await asyncio.sleep(45)

    gmail_task = asyncio.create_task(poll())


@app.on_event("shutdown")
async def shutdown():
    global gmail_task
    if gmail_task:
        gmail_task.cancel()
    client.close()
