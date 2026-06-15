"""
SafeHaven – Supabase Cloud Alert Trigger
=========================================
Sends face-recognition events to the Supabase `alerts` table so the
mobile app can display real-time push notifications.

Table schema expected (alerts):
    id          uuid  (auto)
    type        text  – "KNOWN_PERSON" | "UNKNOWN_PERSON"
    person_name text  – recognised name, or "Unknown"
    confidence  float – cosine similarity score (0–1)
    status      text  – "new" (default)
    user_id     uuid  – references auth.users(id)
    created_at  timestamptz (auto)
"""

import os
import requests

# ── Supabase credentials ──────────────────────────────────────────────────────
SUPABASE_URL = "https://bpndcpacnsglieziysbn.supabase.co"
# Old public (anon) key — used only as a fallback if no key file is present.
_ANON_FALLBACK = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJwbmRjcGFjbnNnbGlleml5c2JuIiwi"
    "cm9sZSI6ImFub24iLCJpYXQiOjE3NzkyODkxNTIsImV4cCI6MjA5NDg2NTE1Mn0"
    ".GRiGTRY7lFswrm613nGpiwvCtfYn9zWqSlbNBUvNjLw"
)


def _load_key():
    """After Phase 2 the Pi uses the service_role key (full access, bypasses
    the per-household rules). Put it in supabase_service_key.txt next to this
    file. Until then, the old anon key is used so nothing breaks."""
    base = os.path.dirname(os.path.abspath(__file__))
    kf = os.path.join(base, "supabase_service_key.txt")
    if os.path.exists(kf):
        v = open(kf).read().strip()
        if v:
            return v
    return _ANON_FALLBACK


SUPABASE_KEY = _load_key()
# ─────────────────────────────────────────────────────────────────────────────

# Every alert from this Pi is routed to the ACCOUNT that owns this Pi's
# household (the account the family photos were uploaded from). That way all
# profiles in that account receive the alert — never filtered by name.
def _resolve_household_owner():
    try:
        base  = os.path.dirname(os.path.abspath(__file__))
        hfile = os.path.join(base, "household_id.txt")
        if not os.path.exists(hfile):
            return None
        hid = open(hfile).read().strip()
        if not hid:
            return None
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/households?id=eq.{hid}&select=owner_id",
            headers={"apikey": SUPABASE_KEY,
                     "Authorization": f"Bearer {SUPABASE_KEY}"},
            timeout=5,
        )
        rows = r.json()
        if rows:
            print(f"[CLOUD] Alerts will be routed to account {rows[0]['owner_id']}")
            return rows[0]["owner_id"]
    except Exception as e:
        print(f"[CLOUD] Could not resolve household owner: {e}")
    return None


USER_ID = _resolve_household_owner()


def send_alert_to_cloud(alert_type, confidence_or_name, confidence=None,
                        user_id=USER_ID, photo_url=None) -> bool:
    """
    Insert one row into the Supabase `alerts` table.
    Supports both signatures:
      - send_alert_to_cloud(alert_type, confidence) -> person_name defaults to "Unknown"
      - send_alert_to_cloud(alert_type, person_name, confidence)
    """
    if confidence is None:
        try:
            actual_confidence = float(confidence_or_name)
            actual_name = "Unknown"
        except (ValueError, TypeError):
            actual_confidence = 1.0
            actual_name = str(confidence_or_name)
    else:
        actual_name = str(confidence_or_name)
        try:
            actual_confidence = float(confidence)
        except (ValueError, TypeError):
            actual_confidence = 1.0

    url     = f"{SUPABASE_URL}/rest/v1/alerts"
    headers = {
        "apikey":        SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type":  "application/json",
        "Prefer":        "return=minimal",
    }
    payload = {
        "type":        alert_type,
        "person_name": actual_name,
        "confidence":  actual_confidence,
        "status":      "new",
    }
    if user_id:
        payload["user_id"] = user_id
    if photo_url:
        payload["photo_url"] = photo_url

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=5)
        if response.status_code in (200, 201):
            print(f"[CLOUD] Alert sent -> type={alert_type}, person={actual_name}")
            return True
        else:
            print(
                f"[CLOUD] Failed ({response.status_code}): {response.text}"
            )
            return False
    except Exception as e:
        print(f"[CLOUD] Connection error: {e}")
        return False


# ── Quick test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Testing Supabase connection...")
    send_alert_to_cloud("KNOWN_PERSON",   "Merna",   0.87)
    send_alert_to_cloud("UNKNOWN_PERSON", 0.21)
