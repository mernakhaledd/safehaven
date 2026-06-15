import requests
import uuid

SUPABASE_URL = "https://bpndcpacnsglieziysbn.supabase.co"
SUPABASE_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJwbmRjcGFjbnNnbGlleml5c2JuIiwi"
    "cm9sZSI6ImFub24iLCJpYXQiOjE3NzkyODkxNTIsImV4cCI6MjA5NDg2NTE1Mn0"
    ".GRiGTRY7lFswrm613nGpiwvCtfYn9zWqSlbNBUvNjLw"
)

def run_e2e_diagnostic():
    # 1. Sign up Care Receiver
    rx_email = f"rx_{uuid.uuid4().hex[:6]}@example.com"
    password = "SuperPassword123"
    print(f"Creating Receiver user: {rx_email}...")
    signup_url = f"{SUPABASE_URL}/auth/v1/signup"
    headers = {"apikey": SUPABASE_KEY, "Content-Type": "application/json"}
    
    rx_resp = requests.post(signup_url, headers=headers, json={"email": rx_email, "password": password})
    rx_data = rx_resp.json()
    rx_id = rx_data["user"]["id"] if "user" in rx_data else rx_data.get("id")
    rx_token = rx_data.get("access_token")
    
    # 2. Sign up Caregiver
    cg_email = f"cg_{uuid.uuid4().hex[:6]}@example.com"
    print(f"Creating Caregiver user: {cg_email}...")
    cg_resp = requests.post(signup_url, headers=headers, json={"email": cg_email, "password": password})
    cg_data = cg_resp.json()
    cg_id = cg_data["user"]["id"] if "user" in cg_data else cg_data.get("id")
    cg_token = cg_data.get("access_token")
    
    # Create profiles
    print("Creating profiles...")
    rx_auth_headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {rx_token}", "Content-Type": "application/json"}
    cg_auth_headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {cg_token}", "Content-Type": "application/json"}
    
    rx_profile_id = str(uuid.uuid4())
    cg_profile_id = str(uuid.uuid4())
    
    requests.post(f"{SUPABASE_URL}/rest/v1/profiles", headers=rx_auth_headers, json={
        "id": rx_profile_id, "user_id": rx_id, "display_name": "DiagnosticRx", "persona": "care_receiver"
    })
    requests.post(f"{SUPABASE_URL}/rest/v1/profiles", headers=cg_auth_headers, json={
        "id": cg_profile_id, "user_id": cg_id, "display_name": "DiagnosticCg", "persona": "care_giver"
    })
    
    # 3. Create a direct profile link
    # We bypass the invite flow by calling a direct insert (or accepting request if needed).
    # Since profile_links has RLS, let's insert a link request and accept it.
    print("Sending link request from Caregiver to Receiver...")
    link_req_id = str(uuid.uuid4())
    req_resp = requests.post(f"{SUPABASE_URL}/rest/v1/link_requests", headers=cg_auth_headers, json={
        "id": link_req_id,
        "from_user_id": cg_id,
        "from_profile_id": cg_profile_id,
        "from_display_name": "DiagnosticCg",
        "to_email": rx_email,
        "status": "pending"
    })
    print(f"Link Request status: {req_resp.status_code}")
    
    print("Accepting link request from Receiver side...")
    accept_resp = requests.post(f"{SUPABASE_URL}/rpc/accept_link_request", headers=rx_auth_headers, json={
        "p_request_id": link_req_id,
        "p_receiver_profile_id": rx_profile_id
    })
    print(f"Accept Link Request RPC status: {accept_resp.status_code} - {accept_resp.text}")
    
    # 4. Trigger manual help request from Receiver (rx)
    print("\nSimulating manual 'Request immediate help' from Receiver...")
    help_payload = [{
        "user_id": rx_id,
        "from_profile_id": rx_profile_id,
        "to_profile_id": cg_profile_id,
        "status": "open"
    }]
    help_resp = requests.post(f"{SUPABASE_URL}/rest/v1/help_requests", headers=rx_auth_headers, json=help_payload)
    print(f"Help Request Insert status: {help_resp.status_code} - {help_resp.text}")
    
    # 5. Insert alert
    print("Inserting alert...")
    alert_payload = {
        "type": "IMMEDIATE_HELP_REQUEST",
        "person_name": "DiagnosticRx",
        "confidence": 1.0,
        "status": "new",
        "user_id": rx_id
    }
    alert_resp = requests.post(f"{SUPABASE_URL}/rest/v1/alerts", headers=rx_auth_headers, json=alert_payload)
    print(f"Alert Insert status: {alert_resp.status_code} - {alert_resp.text}")

if __name__ == "__main__":
    run_e2e_diagnostic()
