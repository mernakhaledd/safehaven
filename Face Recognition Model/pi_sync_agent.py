#!/usr/bin/env python3
"""
SafeHaven — Pi Face Sync Agent (Phase 1)
========================================
Runs forever in the background on the Raspberry Pi.

Every 30 seconds it:
  1. Looks for new (pending) family-member photos in Supabase.
  2. Downloads each photo, finds the face (YuNet) and extracts the
     SFace embedding — using the SAME models as recognize_pi_camera.py.
  3. Saves the embedding back to Supabase (face_embeddings table).
  4. Rebuilds embeddings/embeddings.pkl (your original team faces are
     kept — they are backed up once and always merged back in).
  5. If the face_recognition service is running, restarts it so it
     picks up the new faces immediately.

It does NOT use the camera, so it never conflicts with the models.

Place this file in:  /home/safehaven/face_recognition/Face Recognition Model/
Run via systemd:     see setup_sync_service.sh
"""

import os
import sys
import time
import pickle
import shutil
import subprocess

import cv2
import numpy as np
import requests

# Always work from this script's folder (where the .onnx models live)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)
sys.path.insert(0, BASE_DIR)

from pi_supabase_trigger import SUPABASE_URL, SUPABASE_KEY  # reuse existing config

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
}
JSON_HEADERS = {**HEADERS, "Content-Type": "application/json", "Prefer": "return=minimal"}

POLL_SECONDS    = 30
EMBEDDINGS_PKL  = os.path.join(BASE_DIR, "embeddings", "embeddings.pkl")
LOCAL_BACKUP    = os.path.join(BASE_DIR, "embeddings", "embeddings_local_backup.pkl")

# Same models as enroll.py / recognize_pi_camera.py — loaded once
detector   = cv2.FaceDetectorYN_create("face_detection_yunet_2023mar.onnx", "", (320, 320))
recognizer = cv2.FaceRecognizerSF_create("face_recognition_sface_2021dec.onnx", "")


# ── Supabase helpers ─────────────────────────────────────────────────────────
def api_get(path):
    r = requests.get(f"{SUPABASE_URL}/rest/v1/{path}", headers=HEADERS, timeout=15)
    r.raise_for_status()
    return r.json()


def api_post(table, payload):
    r = requests.post(f"{SUPABASE_URL}/rest/v1/{table}",
                      headers=JSON_HEADERS, json=payload, timeout=15)
    r.raise_for_status()


def api_patch(path, payload):
    r = requests.patch(f"{SUPABASE_URL}/rest/v1/{path}",
                       headers=JSON_HEADERS, json=payload, timeout=15)
    r.raise_for_status()


def download_photo(storage_path):
    url = f"{SUPABASE_URL}/storage/v1/object/authenticated/faces/{storage_path}"
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.content


# ── Embedding extraction (same logic as enroll.py) ───────────────────────────
def extract_embedding(image_bytes):
    """Returns (embedding_list, None) on success or (None, reason) on failure."""
    img_array = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    if img is None:
        return None, "could not read image"

    # Shrink huge phone photos so YuNet works well and fast
    h, w = img.shape[:2]
    if max(h, w) > 1280:
        scale = 1280.0 / max(h, w)
        img = cv2.resize(img, (int(w * scale), int(h * scale)))
        h, w = img.shape[:2]

    detector.setInputSize((w, h))
    _, faces = detector.detect(img)

    if faces is None or len(faces) == 0:
        return None, "no face found in photo"
    if len(faces) > 1:
        return None, "more than one face in photo"

    aligned = recognizer.alignCrop(img, faces[0])
    feature = recognizer.feature(aligned)
    return [float(x) for x in feature[0]], None


# ── This household ────────────────────────────────────────────────────────────
# The Pi belongs to ONE household. Its id is stored in household_id.txt next to
# this script. Only faces registered to THIS household are ever loaded, so a
# person known in one household is "Unknown" in every other household.
HOUSEHOLD_FILE = os.path.join(BASE_DIR, "household_id.txt")


def get_household_id():
    if os.path.exists(HOUSEHOLD_FILE):
        val = open(HOUSEHOLD_FILE).read().strip()
        if val:
            return val
    return None


HOUSEHOLD_ID = get_household_id()


# ── Local cache (embeddings.pkl) ─────────────────────────────────────────────
def rebuild_local_cache():
    """embeddings.pkl = ONLY this household's faces from the cloud.
    No pre-trained / global team faces are ever included."""
    if not HOUSEHOLD_ID:
        print("[SYNC] ⚠ household_id.txt is missing or empty — cannot load faces. "
              "Set it (see setup) and restart.")
        return

    encodings, names = [], []

    query = (f"face_embeddings?household_id=eq.{HOUSEHOLD_ID}"
             "&select=embedding,family_members(display_name)")
    rows = api_get(query)
    for row in rows:
        member = row.get("family_members")
        if not member:
            continue
        encodings.append(np.array(row["embedding"], dtype=np.float32))
        names.append(member["display_name"])

    os.makedirs(os.path.dirname(EMBEDDINGS_PKL), exist_ok=True)
    tmp = EMBEDDINGS_PKL + ".tmp"
    with open(tmp, "wb") as f:
        pickle.dump({"encodings": encodings, "names": names}, f)
    os.replace(tmp, EMBEDDINGS_PKL)
    print(f"[SYNC] embeddings.pkl rebuilt for this household: {len(names)} faces "
          f"({sorted(set(names))})")


def restart_face_service_if_running():
    r = subprocess.run(["systemctl", "is-active", "face_recognition"],
                       capture_output=True, text=True)
    if r.stdout.strip() == "active":
        subprocess.run(["sudo", "systemctl", "restart", "face_recognition"])
        print("[SYNC] face_recognition restarted to load new faces.")


# ── Main work ────────────────────────────────────────────────────────────────
def process_pending_photos():
    """Returns True if anything was processed."""
    pending = api_get(
        "member_photos?status=eq.pending"
        "&select=id,storage_path,member_id,family_members(display_name,household_id)"
    )
    if not pending:
        return False

    for photo in pending:
        pid    = photo["id"]
        member = photo.get("family_members") or {}
        name   = member.get("display_name", "?")

        # Only handle photos that belong to THIS household
        if HOUSEHOLD_ID and member.get("household_id") != HOUSEHOLD_ID:
            continue

        print(f"[SYNC] Processing photo for '{name}' …")

        try:
            image_bytes = download_photo(photo["storage_path"])
            embedding, reason = extract_embedding(image_bytes)

            if embedding is None:
                api_patch(f"member_photos?id=eq.{pid}",
                          {"status": "rejected", "reject_reason": reason})
                print(f"[SYNC]   ✗ rejected: {reason}")
                continue

            api_post("face_embeddings", {
                "member_id": photo["member_id"],
                "household_id": member.get("household_id"),
                "photo_id": pid,
                "embedding": embedding,
            })
            api_patch(f"member_photos?id=eq.{pid}", {"status": "processed"})
            print(f"[SYNC]   ✓ embedded '{name}'")

        except Exception as e:
            print(f"[SYNC]   ! error on photo {pid}: {e}")

    return True


def cloud_signature():
    """Fingerprint of THIS household's embeddings — detects added/deleted people."""
    q = "face_embeddings?select=id"
    if HOUSEHOLD_ID:
        q = f"face_embeddings?household_id=eq.{HOUSEHOLD_ID}&select=id"
    rows = api_get(q)
    return ",".join(sorted(r["id"] for r in rows))


def main():
    print("[SYNC] SafeHaven Face Sync Agent started.")
    print(f"[SYNC] Household: {HOUSEHOLD_ID or 'NOT SET — see household_id.txt'}")

    last_sig = None
    while True:
        try:
            process_pending_photos()
            sig = cloud_signature()
            if sig != last_sig:
                rebuild_local_cache()
                restart_face_service_if_running()
                last_sig = sig
        except Exception as e:
            print(f"[SYNC] Cycle error (will retry): {e}")
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
