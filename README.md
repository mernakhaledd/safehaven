# SafeHaven 🏠

An AI-powered home safety and elderly-care monitoring system built on a
**Raspberry Pi** + camera, a **Supabase** cloud backend, and a **React Native
(Expo)** mobile app.

The Pi watches a home through one camera and runs three on-device AI models that
**recognize faces** (and lock the door on strangers), **detect falls**, and
**detect a "help" hand gesture** — sending real-time alerts (and photos) to a
caregiver's phone. Caregivers register family faces directly from the app
(dynamic enrollment), with per-household data isolation.

## Components

| Part | Tech |
|------|------|
| Face recognition | OpenCV YuNet (detect) + SFace (128-D embeddings), cosine match |
| Fall detection | MediaPipe Pose + TFLite (30-frame sequence) |
| Help gesture | MediaPipe Hands + TFLite (5 consecutive frames @ >0.98) |
| Orchestration | `safehaven_warm.py` — warm-loads models, cycles the camera, boots headless |
| Backend | Supabase (Postgres + Auth + Storage + Realtime, Row-Level Security) |
| Mobile app | Expo / React Native / TypeScript (`Safe Haven/Safe Haven/`) |

## Documentation

- **`PROJECT_DOCUMENTATION.md`** — complete technical record of the whole system
  and everything built (read this first; written for thesis/paper authors).
- **`FACE_ENROLLMENT_ARCHITECTURE.md`** — architecture of the dynamic face
  enrollment design (7-part analysis + repo comparison).

## Repository layout

```
Face Recognition Model/   face model runtime + enrollment + alert helper
mp_fall_project/*         fall model (on the Pi)   — deploy script: 10_mp_pi_deploy.py
help_gesture_project/*    help model (on the Pi)   — deploy script: 6_universal_deploy.py
safehaven_app/            Pi orchestration: warm orchestrator, cycler, control panel, sync agent
Safe Haven/Safe Haven/    the Expo mobile app
supabase_setup_*.sql      database setup (run in the Supabase SQL editor)
```

## Quick start

1. **Supabase:** run `supabase_setup_phase1.sql`, then `supabase_setup_snapshots.sql`,
   then (after putting the service key on the Pi) `supabase_setup_phase2.sql`.
2. **Pi:** install the sync agent and the warm orchestrator
   (`setup_sync_service.sh`, `setup_warm.sh`); power on → it runs headless.
3. **App:** set `EXPO_PUBLIC_SUPABASE_URL` / `EXPO_PUBLIC_SUPABASE_ANON_KEY` in
   `.env`, then `npm install` and `npx expo start` (or `eas build` to ship).

## Notes
- Secrets and private face data are excluded via `.gitignore` (service key,
  household id, enrolled face photos, embeddings). Configure your own before
  running.
- Graduation project — see `PROJECT_DOCUMENTATION.md` §15 for known limitations
  and future work.
