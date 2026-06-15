# SafeHaven — Complete Project Documentation

> Purpose of this file: a single, exhaustive technical record of the SafeHaven
> system and **everything that was built/changed in the latest engineering
> phase**. It is written so another person (or an AI assistant) can understand
> the whole system and write the thesis / research paper from it. It explains
> *what* each part does, *why* it was designed that way, the problems hit, and
> how they were solved.

---

## 1. What SafeHaven Is

SafeHaven is a graduation project: an **AI-powered home safety / elderly-care
monitoring system** built around a **Raspberry Pi** with a camera, three
on-device AI models, a **Supabase** cloud backend, and a **React Native (Expo)
mobile app** for caregivers and care-receivers.

The system watches a home through one Pi camera and can:

- **Recognize faces** at the door (known family members vs. unknown persons),
  and lock the door automatically on an unknown person.
- **Detect falls** (e.g., an elderly person collapsing).
- **Detect a "help" hand gesture** (a person signalling for help).
- **Send real-time alerts** to the caregiver's phone via Supabase.
- **Let caregivers register family faces from the app** (dynamic enrollment).
- **Capture and send photos** (auto-photo of an unknown person; on-demand "live
  photo" of the care-receiver).

### Hardware / runtime
- Raspberry Pi (Bookworm, 64-bit, Python 3) with the official Pi Camera (IMX708).
- Hostname `Safehavenpi1`, user `safehaven`.
- Headless operation (no monitor); administered over SSH and VNC.

---

## 2. The Three AI Models (pre-existing, kept intact)

All three were already trained/working before this phase. A core project rule
was **do not change the models' detection logic** — they work and are validated.

### 2.1 Face Recognition
- **Detection:** OpenCV **YuNet** (`face_detection_yunet_2023mar.onnx`).
- **Recognition:** OpenCV **SFace** (`face_recognition_sface_2021dec.onnx`) →
  produces a **128-dimensional embedding** per face.
- **Matching:** cosine similarity vs. stored embeddings; threshold **0.363**
  (higher = stricter).
- **Camera:** **picamera2** (format BGR888, 640×480).
- **Enrollment:** `enroll.py` reads `dataset/known_faces/<Name>/*.jpg` and writes
  `embeddings/embeddings.pkl` (`{"encodings": [...], "names": [...]}`).
- **Runtime:** `recognize_pi_camera.py` — detects every face, matches, logs
  KNOWN/UNKNOWN, sends an alert to Supabase, and **locks the door** on an unknown.
- **Key insight:** this is **not** a model "trained on the team's faces." SFace
  is a generic pretrained embedder; enrollment only *extracts and stores*
  embeddings. Adding a person = adding embeddings; the model never retrains.
  (This matters for the thesis: say "we *enrolled* faces," not "trained.")

### 2.2 Fall Detection
- **Model:** **MediaPipe Pose** → 33 landmarks (x,y,z,visibility = 132 values)
  per frame, buffered over **30 frames**, fed to a **TFLite** classifier
  (`mp_fall_model.tflite`). Fall when probability **> 0.85**.
- **Camera:** **rpicam-vid** subprocess pipe (YUV420 → BGR/RGB).
- **Runtime:** `10_mp_pi_deploy.py`.
- **Important runtime detail:** the fall `.tflite` uses **Select-TF (Flex) ops**,
  so it requires **full TensorFlow** (`tf.lite.Interpreter`), *not* the
  lightweight `tflite_runtime`. This drove a key decision later (see §8).

### 2.3 Help Gesture
- **Model:** **MediaPipe Hands** → hand landmarks → **TFLite** classifier
  (`help_gesture_model.tflite` + `label_map.json`). Fires only when the
  gesture is seen at **>0.98 confidence for 5 consecutive frames** (anti-false-
  alarm), with prediction smoothing over the last 5 frames.
- **Camera:** **rpicam-vid** subprocess pipe.
- **Runtime:** `6_universal_deploy.py`.

### 2.4 Door Lock
- `door_lock.py` runs as an always-on service; listens to Supabase `door_status`
  and reacts (and face recognition can set `is_locked=true` on unknowns).

### 2.5 Alerts helper
- `pi_supabase_trigger.py` (one per model folder) posts rows to the Supabase
  `alerts` table via the REST API. This file was extended this phase (see §6, §7).

---

## 3. The Mobile App (Expo / React Native)

- **Stack:** Expo SDK 54, React Native 0.81, **expo-router**, TypeScript,
  `@supabase/supabase-js`, `expo-secure-store` (session storage),
  `expo-notifications`.
- **Auth:** Supabase email/password. Session persisted via secure store.
- **Profiles:** "Netflix-style" profiles per account — `care_giver` and
  `care_receiver` (with receiver type: infant/toddler/teen/adult/elder).
- **Screens:** caregiver `home`, `door` (lock), `chats`, `cameras`, `settings`,
  plus `notifications` (live cloud alerts) and the **new `family` tab** (§5).
- **Config:** Supabase URL/anon key come from `EXPO_PUBLIC_SUPABASE_URL` /
  `EXPO_PUBLIC_SUPABASE_ANON_KEY` (in `.env`, read by `src/lib/env.ts`).

---

## 4. The Original Problem & The Journey (chronological)

The Pi models were started **manually from the terminal** (`sudo systemctl start
face_recognition`, etc.), one at a time (only one can use the camera). The
supervisor wanted a more professional, automatic, headless setup. This phase
went through several designs, each replaced by a better one. **All artifacts are
kept** (earlier ones are useful for the paper as "iterations").

1. **Control Panel GUI** (CustomTkinter desktop app) — buttons to start/stop/
   restart/monitor each service + a demo mode. *(Superseded; kept for the paper.)*
2. **Headless auto-cycler** (systemd) — on boot, automatically cycle the models.
   *(Superseded by the warm orchestrator.)*
3. **Warm multi-model orchestrator** (final) — loads the heavy models once and
   rotates the camera; boots headless; self-healing. **This is the production
   design.**

In parallel, a major feature track was added: **dynamic face enrollment from the
app**, **per-household data isolation (security)**, and **photo capture/requests**.

---

## 5. Feature: Dynamic Face Enrollment (app → cloud → Pi)

**Goal:** any signed-in user adds family members from the app (name + photos),
stored in Supabase, and the Pi recognizes them within ~30 s — **no retraining**,
unlimited people, isolated per household.

### 5.1 Why the original approach already "scaled" (analysis)
The system was already embedding-based; the only real gaps were: enrollment was
manual (SSH + copy photos + run `enroll.py`), there was no link between the app
and enrollment, and there was a single global face list with no notion of which
household a face belongs to. So we added plumbing, **not** a new AI model.
(Repos compared in `FACE_ENROLLMENT_ARCHITECTURE.md`: opencv_zoo (YuNet/SFace —
what we use), `ageitgey/face_recognition`, `serengil/deepface`,
`deepinsight/insightface`, `exadel-inc/CompreFace`. Conclusion: keep SFace; it's
the lightest, Pi-appropriate option.)

### 5.2 Supabase schema (`supabase_setup_phase1.sql`)
New tables:
- `households (id, name, owner_id, created_at)`
- `household_members (household_id, user_id, role)`
- `family_members (id, household_id, display_name, created_by, created_at)`
- `member_photos (id, member_id, storage_path, status, reject_reason, created_at)`
  — status: `pending` | `processed` | `rejected`
- `face_embeddings (id, member_id, household_id, photo_id, embedding float8[],
  model_version, created_at)`
- Private Storage bucket **`faces`**.
- Phase 1 used **permissive RLS** (allow all) so nothing breaks while building;
  Phase 2 (§7) replaces this with strict rules.

### 5.3 App: the Family tab (`app/(app)/caregiver/family.tsx`)
- Adds a "Family" tab to the caregiver tab bar (`caregiver/_layout.tsx`).
- User types a name, picks 1–5 photos (`expo-image-picker`), which are uploaded
  to Storage at `faces/{household_id}/{member_id}/{uuid}.jpg`, and a
  `member_photos` row is created (`pending`).
- Auto-creates the user's household on first add (`ensureHousehold`).
- Lists members with status ("Learning…", "✅ Recognized", "❌ rejected").
- Deleting a member cascades (removes photos + embeddings).
- The list is **scoped to the signed-in account's household** (UI-level).

### 5.4 Pi: the Face Sync Agent (`pi_sync_agent.py` + `setup_sync_service.sh`)
A new always-on systemd service (`face_sync`) that every 30 s:
1. Finds `pending` `member_photos` **for this Pi's household**.
2. Downloads each photo, runs **the same YuNet + SFace** code to extract the
   128-D embedding (quality checks: exactly one face, else `rejected`).
3. Inserts the embedding into `face_embeddings` (cloud backup) and marks the
   photo `processed`.
4. Rebuilds the local `embeddings/embeddings.pkl` from **only this household's**
   cloud embeddings, and restarts `face_recognition` if it's running so new
   faces apply immediately.

**Household scoping on the Pi:** the Pi's household id is stored in
`household_id.txt` next to the script. The agent loads **only** that household's
faces, so a face known in one home is "Unknown" at another home's camera.

---

## 6. Fix: Alert Routing (the "only the matching profile sees it" bug)

**Symptom:** a recognized person's alert only reached an account that had a
**profile with the same name**; other profiles/accounts saw nothing.

**Root cause (found in `PASTE_THIS_FOR_ACTIVE_SESSION.sql`):** a database trigger
`auto_assign_alert_user_id` routed each alert by **matching `person_name`
against `profiles.display_name`**. Combined with the `alerts` RLS
(`select using user_id = auth.uid()`), only a name-matched account saw it.

**Fix (Pi side only, no SQL change):** `pi_supabase_trigger.py` now resolves the
**household owner's `user_id`** (via `household_id.txt` → `households.owner_id`)
and stamps every alert with it (`USER_ID = _resolve_household_owner()`). The
trigger skips its name-guess when `user_id` is already set, so every alert goes
to the owning account and **all profiles in that account** receive it.

---

## 7. Phase 2: Real Security (Row-Level Security)

Phase 1 was permissive (the app filtered data, but the database trusted clients).
Phase 2 (`supabase_setup_phase2.sql`) enforces isolation **in the database**:

- A `security definer` helper `my_households()` returns the household ids the
  logged-in user belongs to.
- Strict RLS on `households`, `household_members`, `family_members`,
  `member_photos`, `face_embeddings`, and the `faces` Storage bucket — each
  scoped so an authenticated user only ever reads/writes their own household.
- **The Pi keeps working** because it now authenticates with the Supabase
  **`service_role` key** (full access, bypasses RLS), stored on the Pi in
  `supabase_service_key.txt` (read by `pi_supabase_trigger.py`, falling back to
  the old anon key if the file is absent). The **app** uses the anon key + user
  login, so it is fully locked to its own household.
- Order of operations matters: put the service key on the Pi *before* enabling
  the rules, or the Pi loses access.

**Security note for the paper / before publishing:** the Supabase **anon** key is
still embedded in code (it's a public client key, and with RLS on it can't read
other households). For a real public release it should be rotated and moved to
environment variables; the **service** key must never leave the Pi / be committed.

---

## 8. Feature: Photo Capture & On-Demand Live Photo

(`supabase_setup_snapshots.sql` + edits to `recognize_pi_camera.py`,
`pi_supabase_trigger.py`, and `notifications.tsx`)

- `alerts` gained a `photo_url` column; new private bucket **`snapshots`**; new
  table `photo_requests (id, household_id, requested_by, status, photo_url)`.
- **Auto-photo of an unknown person:** when the face model logs UNKNOWN, it
  captures the current frame, uploads it privately, creates a **7-day signed
  URL**, and attaches it to the alert. The app shows the photo on the alert card.
- **On-demand "live photo":** the app's Notifications screen has a **"Request
  live photo"** button → inserts a `photo_requests` row. The running face model
  polls for pending requests (~every 3 s), grabs a frame, uploads it, and posts a
  "Care Receiver Photo" alert with the image.
- **Fix:** the captured frame must be a **clean copy taken before the detection
  boxes/labels are drawn**, or the photo had red rectangles on it. The app shows
  photos with `resizeMode="contain"` and a 4:3 aspect ratio so they aren't cropped.

---

## 9. Performance Fix: Help Model Latency (camera backlog)

**Symptom:** the help model detected instantly when run fresh/manually but
lagged or missed the gesture when run via services/cycling.

**Root cause (in `6_universal_deploy.py`):** `rpicam-vid` produced 30 fps into a
**100 MB pipe buffer**, but the Pi processed far slower and read **oldest-frame-
first** with no frame dropping — so it analyzed increasingly **stale** frames; the
lag grew over time and with CPU contention. (A secondary amplifier: the alert is
a **synchronous** HTTP POST inside the capture loop.)

**Fix (one-number change on the Pi, backed up first):** lower the camera
`--framerate` from **30 → 10** so the producer roughly matches the consumer and
the buffer stops piling up. This restored near-live detection. (Supabase was
ruled out first — URL correct, insert ~fast.)

A related operational bug was found: **stopping the cycler did not stop the model
it had started**, leaving a model holding the camera (causing fall-alert spam and
blocking the next model). The cycler was given a cleanup trap to stop the current
model on exit.

---

## 10. The Final Design: Warm Multi-Model Orchestrator

(`safehaven_app/safehaven_warm.py` + `setup_warm.sh`)

### 10.1 Why
- Cycling by `systemctl start/stop` **reloads** each model every turn. Help takes
  **~13 s** to load (MediaPipe + TFLite); fall also loads full TensorFlow. In a
  15 s slot that left almost no time to detect.
- Face, by contrast, loads fast and is **very sensitive to its camera**
  (picamera2). Feeding it the shared `rpicam-vid` stream made it flip
  Merna↔Unknown and lag.

### 10.2 The architecture
A single long-running process (run with the **fall venv**, `venv_mp`, which has
**full TensorFlow** for the fall model's Flex ops + mediapipe + opencv):
- **Loads help + fall ONCE** and keeps them warm in memory.
- **Rotates three turns** (15 s each, looping):
  - **FACE turn:** releases the camera and starts the **original
    `face_recognition` service** (picamera2) — *the face model is unchanged and
    runs exactly as before*. Stops it at the end of the turn.
  - **FALL turn / HELP turn:** opens **one** `rpicam-vid` camera and feeds frames
    to the already-loaded model. No reload between turns.
- Only **one camera backend is active at a time** (picamera2 for face, rpicam-vid
  for fall/help), with gaps so the camera is released cleanly on handoff.

### 10.3 Reliability details (hard-won)
- **`venv_mp` (full TF) is mandatory** — the help venv's `tflite_runtime` cannot
  run the fall model's Flex ops (`FlexTensorListReserve`). The model loaders
  prefer `import tensorflow` over `tflite_runtime`.
- **Help reads every frame in sequence** (not "latest only"): MediaPipe Hands
  relies on consecutive frames for tracking; dropping frames broke it. Each turn
  starts with a **camera flush** to discard the previous turn's backlog.
- **Self-healing camera:** reads never block forever (`select` + `os.read` with a
  timeout, frame-aligned via `_read_exact`). If the camera stops delivering
  frames (a **cold-boot handoff race** that made it freeze on the first fall turn
  after reboot), `ensure_camera()` closes and reopens `rpicam-vid` until frames
  flow again. A short startup delay lets the camera stack settle on boot.
- Installed as the systemd service **`safehaven_warm`** (boot-start, headless).
  `setup_warm.sh` disables the old auto-cycler and points `ExecStart` at
  `venv_mp`'s python. Rollback to the old cycler is one command.

### 10.4 Result
Power on the Pi → after ~1 minute it is cycling FACE → FALL → HELP, headless, with
help/fall warm (instant) and face running its exact original code. **Verified to
survive a cold reboot.**

Convenience: a `whichmodel` shell alias prints the currently active model from the
service log.

---

## 11. Mobile App Deployment (EAS)

- `eas.json` defines build profiles: `preview` (installable **APK**, internal
  distribution), `production` (**AAB** for Google Play), each with the Supabase
  `EXPO_PUBLIC_*` env values; `app.json` got an Android `package`
  (`com.safehaven.app`).
- **Android (chosen path):** `eas build -p android --profile preview` → cloud
  build → installable APK link. Google Play (one-time \$25) requires, for new
  personal accounts, a **closed test with 12 testers for 14 days** before
  production — so plan ~2 weeks of lead time.
- **iOS:** Apple Developer Program (\$99/yr); **TestFlight** is the practical way
  to put it on iPhones without full App Store review.
- **Updates after release:** JS/UI changes ship instantly via **EAS Update** (OTA,
  no rebuild); native changes need a new build.

---

## 12. File / Component Map (what lives where)

**Pi — model runtimes (unchanged logic):**
- `face_recognition/Face Recognition Model/recognize_pi_camera.py` (face; +photo
  capture & photo-request polling added), `enroll.py`, the two `.onnx` models,
  `embeddings/embeddings.pkl`, `pi_supabase_trigger.py` (alert helper; household
  routing + service-key loader added), `household_id.txt`, `supabase_service_key.txt`.
- `mp_fall_project/10_mp_pi_deploy.py` (fall), `mp_fall_model.tflite`.
- `help_gesture_project/6_universal_deploy.py` (help; framerate 30→10),
  `help_gesture_model.tflite`, `label_map.json`.
- `door_lock.py` (door service).

**Pi — orchestration (new this phase, in `safehaven_app/`):**
- `safehaven_control.py` + `install_app.sh` — CustomTkinter control panel (iter 1).
- `safehaven_autocycler.sh` + `setup_autocycler.sh` — headless cycler (iter 2).
- `safehaven_warm.py` + `setup_warm.sh` — **warm orchestrator (final)**.
- `pi_sync_agent.py` + `setup_sync_service.sh` — face enrollment sync agent.

**Supabase SQL (run in the dashboard):**
- `supabase_setup_phase1.sql` (enrollment tables, permissive RLS, faces bucket)
- `supabase_setup_phase2.sql` (strict RLS + my_households())
- `supabase_setup_snapshots.sql` (photo_url, snapshots bucket, photo_requests)
- existing: `PASTE_THIS_FOR_ACTIVE_SESSION.sql`, `PASTE_THIS_TO_RESTORE_ALERTS.sql`,
  `PASTE_THIS_FOR_DOOR_LOGS.sql`.

**Mobile app (`Safe Haven/Safe Haven/`):**
- `app/(app)/caregiver/family.tsx` (new Family tab), `caregiver/_layout.tsx` (tab),
  `app/(app)/notifications.tsx` (photos + request button), `eas.json`, `app.json`.

**Docs:**
- `FACE_ENROLLMENT_ARCHITECTURE.md` (the 7-part architecture analysis).
- `PROJECT_DOCUMENTATION.md` (this file).

---

## 13. Data Flows (for diagrams in the thesis)

**Enrollment:** App (photo+name) → Supabase Storage `faces/` + `member_photos`
(pending) → Pi `face_sync` agent downloads → YuNet+SFace embedding →
`face_embeddings` (cloud) + local `embeddings.pkl` → `face_recognition` reloads.

**Recognition + alert:** Camera → model → detection → `pi_supabase_trigger`
inserts into `alerts` (stamped with household owner's `user_id`, optional
`photo_url`) → Supabase Realtime → app shows alert (RLS ensures only the owning
household sees it).

**On-demand photo:** App inserts `photo_requests` (pending) → running face model
grabs a frame → uploads to `snapshots` + signed URL → updates the request and
posts a "Care Receiver Photo" alert → app displays it.

**Model scheduling:** `safehaven_warm` (boot service) → loads help+fall once →
loops: face service (picamera2) ↔ rpicam-vid (fall, help), one camera at a time.

---

## 14. Key Engineering Decisions & Lessons (good "discussion" material)

- **One physical camera ⇒ one model at a time.** All scheduling complexity stems
  from this hardware constraint.
- **Cold-start vs. warm-start.** Re-`exec`ing a Python+TF+MediaPipe process costs
  ~13 s; keeping models resident eliminates it. This justified the orchestrator.
- **Different camera backends matter.** picamera2 gives the freshest frame and
  suits face; `rpicam-vid` pipes can accumulate latency — fixed by lowering
  framerate and flushing per turn.
- **Runtime mismatch (Flex ops).** The fall model needs full TensorFlow; a single
  shared environment had to be chosen carefully (`venv_mp`).
- **Multi-tenancy via RLS.** Household isolation belongs in the database, with the
  device using a service key — not just hidden in the app.
- **Don't touch what works.** The face model especially was kept byte-identical;
  problems were solved around it (camera handoff) rather than inside it.
- **Robustness for unattended boot.** Self-healing camera + retries are what make
  a demo "just work" after a power cycle.

---

## 15. Known Limitations & Future Work

- **Face threshold variance:** at 0.363, lighting/angle can flip a known person to
  Unknown. Mitigation: enroll more varied photos per person; or tune threshold.
- **One Pi = one household:** switching households needs editing `household_id.txt`.
  A future **device-pairing flow (Phase 3)** would let a user pair a Pi to their
  household from the app with a code (no file editing), enabling true multi-Pi
  multi-household deployments.
- **Time-sliced monitoring:** each model watches ~1/3 of the time. A future "all
  models on every frame" pipeline (one camera backend, all models warm) would
  make everything always-on — bigger rewrite, needs a combined environment.
- **Secrets:** rotate the Supabase anon key and move keys to env vars for a public
  release; keep the service key only on the device.

---

## 16. How to Run / Reproduce (quick reference)

- **Bring up the Pi monitoring (headless):** power on → `safehaven_warm` service
  auto-starts → cycles the three models. Watch: `journalctl -u safehaven_warm -f`.
- **Add a family face:** app → caregiver → Family tab → name + photos →
  `face_sync` enrolls within ~30 s.
- **See alerts / photos:** app → Notifications (live via Supabase Realtime).
- **Build the app:** in the app folder, `eas build -p android --profile preview`.
- **Supabase setup (once):** run the three `supabase_setup_*.sql` files in order
  (phase1 → snapshots → phase2), put the service key on the Pi before phase2.
