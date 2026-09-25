# Fmail — Personal Communication OS (PRD)

## Original Problem Statement
Build "Fmail", a production-ready Personal Communication OS unifying Email, AI, Calendar, Tasks,
Contacts, Files, Meetings, Memory, AI Agents and an AI Representative inside ONE Expo app.
Fmail Meet is a native module inside the app (not separate). Core loop:
Receive → Understand → Remember → Decide → Act → Learn. Palette: primary #FF5E00, bg #F5F6F8,
text #1C1C1E. Firebase set up app-wide. Voice via Sarvam AI. Light/Dark/System themes.

## Architecture
- Frontend: Expo Router (React Native), react-query, react-native-keyboard-controller,
  @react-native-vector-icons, expo-audio/camera/document-picker, Firebase JS SDK (initialized app-wide).
  Theme tokens in src/theme.ts (light+dark). Shared UI in src/ui.tsx, header in src/screen.tsx.
  Navigation: 4 tabs (Home, Mail, Meet, Ask Fmail) + Home hub grid to all other modules.
- Backend: FastAPI + MongoDB (motor), uuid string ids, JWT auth (bcrypt). AI via emergentintegrations
  (gpt-5.4) with graceful JSON fallbacks. Sarvam AI for STT + translation.
- Auth: backend JWT (works in Expo Go). Firebase config present for future native features.

## User Personas
- Founder / professional drowning in scattered communication who wants AI to understand, remember and act.
- Student / individual wanting a unified inbox + calendar + tasks + meetings with an AI chief of staff.

## Core Requirements (static)
Unified inbox with AI classification; Ask Fmail RAG assistant; email understanding + thread summaries;
AI reply writer (tones/rewrites); email→task/reminder/calendar; follow-up brain; calendar; tasks;
files + attachment brain; contacts + communication graph; memory; spaces/rooms; Fmail Meet with
copilot (transcript, captions, AI notes, ask meeting); AI Representative with scoped permissions +
human handoff; AI Agents marketplace + builder; universal search; audit log; daily brief/command center;
voice dictation + translation (Sarvam); light/dark/system; app-wide error/loading states.

## Implemented (2026-06 — Iteration 1, MVP complete & tested)
- Auth: signup (creates name@fmails.in identity + auto-seeds rich demo data), login, profile, JWT.
- Home command center: AI daily brief, quick actions, stat strip, needs-action/meetings, module hub.
- Universal Inbox: folders, filter + account + category chips, thread view, compose/send/draft, star/archive/trash.
- AI: understand (structured), thread summary, reply writer (8 tones + rewrites), Ask Fmail chat (RAG),
  email→task, file summary. All via gpt-5.4 with fallbacks.
- Calendar (month view + events), Tasks (CRUD, priority/labels), Contacts (+graph), Files (upload + AI summary),
  Memory (kinds + CRUD), Spaces, Follow-ups, Audit log, Search (grouped semantic).
- Fmail Meet: start meeting, in-call controls (mic/cam/screen/captions), end→AI notes, transcript, Ask Meeting.
- AI Representative: modes, instructions, negotiation floor, scoped permissions, human-handoff preview.
- AI Agents: 15-agent marketplace w/ categories, install/toggle/uninstall, Agent Builder.
- Voice: Sarvam dictation (permission flow) + translation. Settings: profile, connected accounts,
  AI/memory toggles, theme, Firebase connected. Full light/dark theme.
- Verified: 30/30 backend tests pass, full frontend E2E pass.

## Backlog (prioritized)
- P1: Real WebRTC video in Meet (currently simulated call UI); live transcription streaming during call.
- P1: Google sign-in (needs OAuth web client id) + real Gmail/Outlook account connect (OAuth + sync).
- P2: Push notifications (on user request; needs deploy + build); agent triggers/automation runtime.
- P2: Whiteboard, presentation assistant, decision/commitment dedicated screens, offline caching.

## Next Tasks
- Gather OAuth credentials to enable real Google sign-in and Gmail/Outlook sync.
- Decide on WebRTC provider for real Meet video before hardening the meeting module.
