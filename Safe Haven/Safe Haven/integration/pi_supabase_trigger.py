import requests
import json
import time

# Supabase Configuration
SUPABASE_URL = "https://bpndcpacnsglieziysbn.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJwbmRjcGFjbnNnbGlleml5c2JuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzkyODkxNTIsImV4cCI6MjA5NDg2NTE1Mn0.GRiGTRY7lFswrm613nGpiwvCtfYn9zWqSlbNBUvNjLw"

# User ID to associate alerts with (find it in your Supabase Auth Dashboard)
USER_ID = None  # e.g. "b1d733dc-e761-490d-9b66-2dc5a56c4015"

def send_alert_to_cloud(alert_type, confidence_or_name, confidence=None, user_id=USER_ID):
    """
    Sends an alert directly to Supabase via REST API.
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

    url = f"{SUPABASE_URL}/rest/v1/alerts"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    
    payload = {
        "type": alert_type,
        "confidence": actual_confidence,
        "person_name": actual_name,
        "status": "new"
    }
    if user_id:
        payload["user_id"] = user_id
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=5)
        if response.status_code in [200, 201]:
            print(f"[CLOUD] Alert Sent to Supabase: {alert_type}")
            return True
        else:
            print(f"[CLOUD] Failed to send: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"[CLOUD] Connection Error: {e}")
        return False

# Test function if run directly
if __name__ == "__main__":
    print("Testing connection to Supabase...")
    send_alert_to_cloud("TEST_ALERT", 0.99)
