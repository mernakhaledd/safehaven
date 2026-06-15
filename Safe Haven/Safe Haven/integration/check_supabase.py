import requests

SUPABASE_URL = "https://bpndcpacnsglieziysbn.supabase.co"
SUPABASE_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJwbmRjcGFjbnNnbGlleml5c2JuIiwi"
    "cm9sZSI6ImFub24iLCJpYXQiOjE3NzkyODkxNTIsImV4cCI6MjA5NDg2NTE1Mn0"
    ".GRiGTRY7lFswrm613nGpiwvCtfYn9zWqSlbNBUvNjLw"
)

def check_database():
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    
    # 1. Test fetching alerts (GET)
    print("1. Fetching alerts via REST API...")
    url = f"{SUPABASE_URL}/rest/v1/alerts?limit=5"
    try:
        response = requests.get(url, headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error fetching alerts: {e}")

    # 2. Test inserting a test alert (POST) with user_id = null and return=minimal
    print("\n2. Trying to insert a test alert with null user_id...")
    url = f"{SUPABASE_URL}/rest/v1/alerts"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    payload = {
        "type": "DIAGNOSTIC_TEST_NULL_USER_ID",
        "confidence": 0.95,
        "person_name": "Unknown",
        "status": "new"
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error inserting alert: {e}")

if __name__ == "__main__":
    check_database()
