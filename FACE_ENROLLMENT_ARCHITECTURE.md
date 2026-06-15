# SafeHaven — Dynamic Face Enrollment Architecture

**Goal:** let any signed-in user add family members from the mobile app (photo + name), store them in Supabase, and have the Raspberry Pi recognize them immediately — no retraining, unlimited people, multiple households.

This document is based on a direct review of the actual codebase: `Face Recognition Model/` (enroll.py, recognize_pi_camera.py, evaluate.py, the YuNet/SFace ONNX models), the Expo app (`Safe Haven/Safe Haven/`), `pi_supabase_trigger.py`, and `setup_services.sh`.

---

## Part 1 — Analysis of the Current Implementation

### What you actually have (verified from code)

| Stage | Implementation |
|---|---|
| Face detection | **YuNet** (`face_detection_yunet_2023mar.onnx`) via `cv2.FaceDetectorYN` |
| Face recognition | **SFace** (`face_recognition_sface_2021dec.onnx`) via `cv2.FaceRecognizerSF` — produces a **128-D embedding** per face |
| Matching | Cosine similarity against stored embeddings, threshold `0.363` |
| Enrollment | `enroll.py` reads `dataset/known_faces/<Name>/*.jpg` → writes `embeddings/embeddings.pkl` |
| Runtime | `recognize_pi_camera.py` loads the .pkl once at startup, matches every detected face |
| Alerts | `pi_supabase_trigger.py` POSTs to the Supabase `alerts` table (also locks `door_status` on Unknown) |

### Verdict: the approach is NOT fundamentally wrong

This is the most important finding. **You never "trained" a model on your team's faces.** SFace is a generic, pre-trained face embedding model — `enroll.py` only *extracts embeddings* from your photos and stores them. Your system is already:

- ✅ Embedding-based (the architecture your supervisor described)
- ✅ Retraining-free — adding a person = adding embeddings, the model never changes
- ✅ Capable of unlimited people

The phrase "we trained it on our faces" in your report should be corrected to "we *enrolled* our faces" — examiners will care about this distinction, and it works in your favor.

### What actually doesn't scale (the real gaps)

1. **Enrollment is manual and physical.** Adding a person requires SSH access to the Pi, copying photos into a folder, and running `enroll.py`. A real user can't do this.
2. **No connection between the app and enrollment.** The app's `profiles` table (see `profiles/new.tsx`) stores names/personas but has no photos and no link to face data.
3. **Single global face list.** One `embeddings.pkl` on one Pi. No concept of *whose* family these faces are — no `household_id` anywhere.
4. **Alerts are unscoped.** `pi_supabase_trigger.py` has `USER_ID = None`, so alerts aren't tied to a user/household — any app user would see everyone's alerts.
5. **No lifecycle management.** No way to update photos, delete a person, or see who is enrolled from the app.
6. **Embeddings only live on the Pi.** If the SD card dies, enrollment is lost; a second Pi can't share them.
7. **Secrets hardcoded.** The Supabase URL/key are committed in `pi_supabase_trigger.py`. With no Row-Level Security, the anon key can read/write everything — fatal for multi-household. (Also: this key has been shared in chats/repos — **rotate it** before submission.)
8. Legacy: `integration/pi_server.py` (local Flask polling) is superseded by the direct-Supabase path and should be retired.

---

## Part 2 — Recommended Solution

### Keep SFace on the Pi. Build the missing pipeline around it.

**Recommendation: do NOT replace YuNet + SFace.** It is already the right class of solution for a Pi: pure OpenCV, no TensorFlow/dlib/PyTorch, proven working on *your* hardware at usable FPS. What's missing is plumbing, not AI.

### Target architecture

```
┌─────────────┐  photo+name   ┌──────────────────────────┐
│  Mobile App │ ────────────▶ │         Supabase          │
│ (Expo RN)   │               │  Auth · Postgres · Storage│
│             │ ◀──────────── │  family_members            │
│  alerts,    │   realtime    │  member_photos             │
│  member list│               │  face_embeddings           │
└─────────────┘               │  households · devices      │
                              └─────────▲────────┬────────┘
                                        │ upload │ download photos,
                             embeddings │        │ poll/realtime changes
                              ┌─────────┴────────▼────────┐
                              │  Raspberry Pi (per house)  │
                              │  pi_sync_agent.py (NEW,    │
                              │   always-on systemd svc)   │
                              │  → runs SFace on new photos│
                              │  → writes face_embeddings  │
                              │  → maintains local cache   │
                              │  recognize_pi_camera.py    │
                              │   (hot-reloads cache)      │
                              └────────────────────────────┘
```

### Why embeddings are extracted **on the Pi**

| Option | Verdict |
|---|---|
| **On the Pi (chosen)** | Reuses your exact SFace code, so enrolled embeddings are guaranteed compatible with the matcher. Zero new infrastructure. The Pi must be online anyway. |
| Cloud Python service | More "SaaS-like", but adds a server to build/host/pay for, and you must keep its SFace version byte-identical to the Pi's. Overkill for this project. |
| Supabase Edge Function | Edge Functions run Deno/JS — OpenCV SFace isn't practically available there. ❌ |
| In the mobile app | Would require a different model on-device; embeddings from different models are incompatible. ❌ |

Embeddings are *also* written back to Supabase (`face_embeddings` table), which gives you: backup, instant enrollment on a replacement/second Pi, and an authoritative cloud copy per household.

### Multi-household model

- A **household** groups users, family members, and devices.
- Every Pi is a **device** registered to exactly one household via a one-time **pairing code** shown in the app.
- Each Pi authenticates to Supabase as its own auth user (a "device account" created during pairing), so **Row-Level Security** can scope every table by household. The anon key alone can no longer read anything.
- The recognizer loads only its household's embeddings; alerts carry `household_id`, and the app shows only your household's alerts.

---

## Part 3 — Repository Research

Comparison of the well-known open-source options for embedding-based recognition with dynamic enrollment:

| Project | What it is | Pi suitability | Dynamic enrollment | Trade-offs |
|---|---|---|---|---|
| **[opencv_zoo — YuNet + SFace](https://github.com/opencv/opencv_zoo)** (what you use) | Official OpenCV model zoo; lightweight ONNX detector + 128-D embedder | ★★★★★ pure `opencv-python`, CPU-friendly | Yes — store/compare embeddings yourself (you already do) | Slightly lower accuracy than ArcFace-class models; you own the plumbing |
| **[ageitgey/face_recognition](https://github.com/ageitgey/face_recognition)** | The most-starred Python face lib (dlib HOG/CNN + 128-D embeddings) | ★★ dlib compiles painfully on Pi; CNN mode too slow | Yes (`known_faces` folder pattern — likely what your supervisor remembers) | Effectively in maintenance mode; slower and heavier than your current stack — **switching would be a downgrade** |
| **[serengil/deepface](https://github.com/serengil/deepface)** | High-level wrapper over many models (FaceNet, ArcFace, SFace…), REST API | ★★ pulls in TensorFlow; heavy for Pi | Yes (`DeepFace.find` over a db folder) | Excellent for a *server-side* extractor if you ever move embedding extraction to the cloud |
| **[deepinsight/insightface](https://github.com/deepinsight/insightface)** | State-of-the-art ArcFace family (`buffalo_l` etc.), ONNX runtime | ★★★ runs on Pi via onnxruntime but slower than SFace | Yes (embeddings) | Best accuracy (~99.8% LFW). Your **upgrade path** if SFace accuracy disappoints: swap the ONNX model + re-extract embeddings; architecture unchanged |
| **[exadel-inc/CompreFace](https://github.com/exadel-inc/CompreFace)** | Self-hosted face recognition *service* (Docker, REST API, admin UI, built on FaceNet/InsightFace) | ★ needs multi-GB Docker stack — not for a Pi 4/5 alongside your other models | Yes — its core feature (Face Collections API) | The "buy not build" option: closest to a production product, but it replaces your whole pipeline and needs a real server |

**Conclusion:** your supervisor's described pattern (generic model + faces stored separately + no retraining) is exactly the `face_recognition`/CompreFace pattern — **and your code already implements it** with a lighter, more Pi-appropriate stack. Keep it. Cite opencv_zoo as your foundation; mention InsightFace as the documented accuracy upgrade path.

---

## Part 4 — Integration Plan

### Flow A — Enrollment (app → Pi)

1. User signs in (existing Supabase Auth) and opens **Manage Family Members** (new screens beside `app/(app)/profiles/`).
2. Picks 1–5 photos (`expo-image-picker`) and enters a name.
3. App inserts a row in `family_members`, uploads photos to Storage at `faces/{household_id}/{member_id}/{uuid}.jpg`, inserts `member_photos` rows (status `pending`).
4. **pi_sync_agent.py** (new always-on service on the Pi, like `door_lock`) listens via Supabase Realtime on `member_photos` (fallback: poll every 30 s).
5. For each pending photo: download → YuNet detect → quality check (exactly one face, min size) → SFace embedding → insert into `face_embeddings` → mark photo `processed` (or `rejected: no_face`, which the app shows to the user).
6. Agent rebuilds the local cache `embeddings/embeddings.json` and touches a flag file.
7. `recognize_pi_camera.py` checks the flag's mtime each loop and hot-reloads — **the new person is recognized within seconds, no service restart.**

### Flow B — Recognition + alert (existing, scoped)

Camera frame → YuNet → SFace embedding → cosine vs household embeddings → known: alert `"{name} Detected at the Door"`; unknown: alert + door lock (existing logic). The only change: alerts now include `household_id` (+ `member_id` when known).

### Flow C — Removal

App deletes `family_member` → cascade deletes photos + embeddings → Realtime event → agent rebuilds cache. Person stops being recognized within seconds.

### Flow D — Device pairing (multi-household)

1. App (household owner) generates a 6-digit code → row in `pairing_codes` (expires 10 min).
2. On the Pi: `python pair_device.py` → user types the code → an Edge Function (or RPC) validates it, creates a device auth account bound to that household, returns credentials.
3. Pi stores credentials in `/home/safehaven/.safehaven/device.json` (chmod 600). All Pi→Supabase calls now use this authenticated session — **delete the hardcoded anon-key usage**.

---

## Part 5 — Database Design (Supabase)

```sql
-- Households & membership ------------------------------------------------
create table households (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  owner_id uuid not null references auth.users(id),
  created_at timestamptz default now()
);

create table household_members (        -- app users belonging to a household
  household_id uuid references households(id) on delete cascade,
  user_id uuid references auth.users(id) on delete cascade,
  role text not null default 'member',  -- 'owner' | 'member'
  primary key (household_id, user_id)
);

-- People to recognize ------------------------------------------------------
create table family_members (
  id uuid primary key default gen_random_uuid(),
  household_id uuid not null references households(id) on delete cascade,
  display_name text not null,
  created_by uuid references auth.users(id),
  created_at timestamptz default now()
);

create table member_photos (
  id uuid primary key default gen_random_uuid(),
  member_id uuid not null references family_members(id) on delete cascade,
  storage_path text not null,             -- faces/{household}/{member}/{uuid}.jpg
  status text not null default 'pending', -- pending | processed | rejected
  reject_reason text,
  created_at timestamptz default now()
);

create table face_embeddings (
  id uuid primary key default gen_random_uuid(),
  member_id uuid not null references family_members(id) on delete cascade,
  household_id uuid not null references households(id) on delete cascade,
  photo_id uuid references member_photos(id) on delete cascade,
  embedding float8[] not null,            -- 128 floats (SFace)
  model_version text not null default 'sface_2021dec',
  created_at timestamptz default now()
);

-- Devices (Raspberry Pis) ---------------------------------------------------
create table devices (
  id uuid primary key default gen_random_uuid(),
  household_id uuid not null references households(id) on delete cascade,
  device_user_id uuid references auth.users(id),  -- the Pi's auth account
  name text default 'SafeHaven Pi',
  last_seen_at timestamptz
);

create table pairing_codes (
  code text primary key,
  household_id uuid not null references households(id) on delete cascade,
  expires_at timestamptz not null,
  used boolean default false
);

-- Existing tables: add scoping ----------------------------------------------
alter table alerts add column household_id uuid references households(id);
alter table alerts add column member_id uuid references family_members(id);
alter table door_status add column household_id uuid references households(id);
```

**Row-Level Security (the multi-household guarantee).** Enable RLS on every table; one policy pattern covers them all:

```sql
create policy "household members read"
on family_members for select using (
  household_id in (select household_id from household_members
                   where user_id = auth.uid())
  or household_id in (select household_id from devices
                      where device_user_id = auth.uid())
);
-- repeat (select/insert/update/delete as appropriate) for member_photos,
-- face_embeddings, devices, alerts, door_status, households
```

**Storage:** private bucket `faces`; policy mirrors the same household check via path prefix `faces/{household_id}/…`.

Notes: `float8[]` is sufficient (a household has tens of faces — brute-force cosine on the Pi is microseconds; you don't need pgvector, though it's a drop-in later). `model_version` lets you migrate to InsightFace later without ambiguity.

---

## Part 6 — Code Changes

### Unchanged (the "models" — per project rule, untouched)
- Both `.onnx` files, the YuNet/SFace detection + matching logic, threshold, fall/gesture models, door lock flow.

### Modified
| File | Change |
|---|---|
| `recognize_pi_camera.py` | Load embeddings from the agent-maintained cache (JSON instead of pkl); hot-reload when the flag file changes; include `household_id`/`member_id` in alerts. ~30 lines. |
| `pi_supabase_trigger.py` | Read URL/credentials from `device.json` instead of hardcoded constants; add `household_id` to payloads. |
| `enroll.py` | Extract its core into `face_embedding.py` (`extract_embedding(image) -> list[float] \| None`) shared by enroll.py (kept for offline dev) and the new agent. |
| `setup_services.sh` | Add `pi_sync_agent.service` (always-on, like door_lock). |
| App `profiles/*` | Either extend, or add a parallel **family-members/** section: list, add (name + photos via `expo-image-picker`), delete, photo status (pending/processed/rejected). Reuses your existing Card/Button/Screen components and supabase client. |

### New
- **Pi:** `pi_sync_agent.py` (download photos, embed, upsert, rebuild cache), `pair_device.py`, `~/.safehaven/device.json`.
- **App:** `app/(app)/family-members/index.tsx`, `new.tsx`; household creation/join + pairing-code screen.
- **Supabase:** SQL from Part 5; pairing Edge Function (or `security definer` RPC).

### Removed / retired
- `integration/pi_server.py` (legacy local Flask path).
- Hardcoded Supabase keys (rotate the anon key — it's in the repo and chat history).
- `dataset/known_faces` as the production enrollment path (keep for development only).

---

## Part 7 — Step-by-Step Implementation Roadmap

Ordered so every step leaves the system working; one person can own each track.

1. **Schema (½ day).** Run Part 5 SQL in Supabase; create `faces` bucket; enable RLS but add a temporary permissive policy so nothing breaks yet.
2. **App: family members UI (1–2 days).** List/add/delete screens; photo upload to Storage; rows in `family_members` + `member_photos`. Verify in the Supabase dashboard that photos and rows appear.
3. **Pi: `face_embedding.py` refactor (½ day).** Extract the shared function; `enroll.py` keeps working — proves no model behavior changed.
4. **Pi: `pi_sync_agent.py`, single household (2 days).** Hardcode your own `household_id` first. Poll every 30 s → process pending photos → write `face_embeddings` → rebuild local cache. Acceptance test: add yourself in the app, photo flips to `processed`, embedding row exists.
5. **Pi: hot-reload in `recognize_pi_camera.py` (½ day).** End-to-end test: enroll a *new* person from the phone → walk in front of the camera → named alert appears in the app. **This is your demo money-shot; record it.**
6. **Scoping (1 day).** `household_id` on alerts/door; app filters by household. Real RLS policies replace the permissive one.
7. **Device pairing (1–2 days).** Pairing code flow + device auth account; agent and trigger switch to `device.json` credentials; delete hardcoded keys; rotate anon key.
8. **Second household proof (½ day).** Second Supabase user + household; their family member must NOT be recognized by your Pi, and they must not see your alerts. Screenshot for the report — this is your multi-tenancy evidence. (A laptop running `recognize.py` can play the role of a second household's "Pi".)
9. **Quality & threshold validation (½ day).** Extend `evaluate.py` to pull embeddings from Supabase; confirm 0.363 still behaves with phone-quality photos; document FAR/FRR informally.
10. **Cleanup & docs (½ day).** Retire `pi_server.py`, update README, add the architecture diagram to the report, fix "trained" → "enrolled" wording.

**Total: roughly 8–10 working days** for the full multi-household build (steps 1–5 alone, ~5 days, already give you the demo-able dynamic enrollment).

### Open questions (couldn't be verified from the codebase — confirm before step 1)
- The live Supabase schema for `profiles`/`alerts` (I inferred from app code; export it from the dashboard before altering).
- Whether `door_lock.py` (referenced in `setup_services.sh`) also uses the hardcoded key — update it in step 7 if so.
- Pi model/RAM (affects how many photos the agent should process in parallel — default to one at a time).
