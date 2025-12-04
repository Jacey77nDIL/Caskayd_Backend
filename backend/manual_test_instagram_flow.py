import os
import sys
import requests
import json
import time
import webbrowser
from urllib.parse import urlencode

# Try to load .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not installed. Assuming env vars are set.")

# Configuration
BASE_URL = "http://localhost:8000"
FB_APP_ID = os.getenv("FB_APP_ID")
REDIRECT_URI = os.getenv("FACEBOOK_REDIRECT_URI")

if not FB_APP_ID or not REDIRECT_URI:
    print("Error: FB_APP_ID and FACEBOOK_REDIRECT_URI must be set in .env file")
    sys.exit(1)

def create_test_user():
    """Creates a random test user to get a valid JWT token"""
    timestamp = int(time.time())
    email = f"test_user_{timestamp}@example.com"
    password = "password123"
    
    print(f"\n1. Creating test user: {email}")
    
    payload = {
        "email": email,
        "password": password,
        "role": "creator",
        "category": "Lifestyle",
        "name": "Test User",
        "bio": "This is a test user"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/signup/creator", json=payload)
        if response.status_code == 200:
            token = response.json()["access_token"]
            print("   ✅ User created successfully")
            return token, email
        elif response.status_code == 400 and "already exists" in response.text:
            # Try login instead
            print("   User exists, logging in...")
            login_payload = {"email": email, "password": password}
            login_resp = requests.post(f"{BASE_URL}/login", json=login_payload)
            if login_resp.status_code == 200:
                token = login_resp.json()["access_token"]
                print("   ✅ Logged in successfully")
                return token, email
            
        print(f"   ❌ Failed to create/login user: {response.text}")
        sys.exit(1)
    except Exception as e:
        print(f"   ❌ Connection error: {e}")
        print("   Make sure the backend server is running on http://localhost:8000")
        sys.exit(1)

def get_user_id(token):
    """Decodes the token to get user info (by calling an endpoint)"""
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"{BASE_URL}/get_current_user", headers=headers)
    # This endpoint returns email and role, but not ID. 
    # We'll need the ID for the analytics endpoint.
    # However, the /auth/facebook endpoint extracts ID from token.
    # The analytics endpoint /api/analytics/instagram/{user_id} needs ID.
    # We can get the ID from the response of /auth/facebook which returns the analytics object including user_id.
    return resp.json()

def start_oauth_flow():
    """Generates the Facebook Login URL"""
    print("\n2. Starting OAuth Flow")
    
    params = {
        "client_id": FB_APP_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": "instagram_basic,instagram_manage_insights,pages_show_list,pages_read_engagement",
        "response_type": "code",
    }
    
    auth_url = f"https://www.facebook.com/v19.0/dialog/oauth?{urlencode(params)}"
    
    print("\n" + "="*80)
    print("ACTION REQUIRED: Open the following URL in your browser:")
    print("-" * 80)
    print(auth_url)
    print("-" * 80)
    print("="*80)
    
    # Optional: Open browser automatically
    # webbrowser.open(auth_url)
    
    print("\nAfter logging in and authorizing, you will be redirected to a URL like:")
    print(f"{REDIRECT_URI}?code=...")
    print("\nCopy the 'code' parameter from the URL and paste it below.")
    
    code = input("\nEnter the code here: ").strip()
    return code

def exchange_code(token, code):
    """Exchanges the code for a token via the backend"""
    print("\n3. Exchanging code for access token...")
    
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"code": code}
    
    try:
        response = requests.post(f"{BASE_URL}/auth/facebook", json=payload, headers=headers)
        
        if response.status_code == 200:
            print("   ✅ Token exchange successful!")
            data = response.json()
            print(json.dumps(data, indent=2))
            return data.get("data", {}).get("user_id")
        else:
            print(f"   ❌ Failed: {response.status_code}")
            print(response.text)
            return None
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None

def test_analytics_endpoints(token, user_id):
    """Tests the analytics endpoints"""
    if not user_id:
        print("Skipping analytics test due to missing user_id")
        return

    print(f"\n4. Testing Analytics Endpoints for User ID: {user_id}")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test 1: Get Analytics
    print("\n   a. Fetching Analytics...")
    resp = requests.get(f"{BASE_URL}/api/analytics/instagram/{user_id}", headers=headers)
    if resp.status_code == 200:
        print("      ✅ Success")
        print(json.dumps(resp.json(), indent=2))
    else:
        print(f"      ❌ Failed: {resp.status_code} - {resp.text}")

    # Test 2: Get Trends
    print("\n   b. Fetching Trends...")
    resp = requests.get(f"{BASE_URL}/api/analytics/instagram/{user_id}/trends", headers=headers)
    if resp.status_code == 200:
        print("      ✅ Success")
        print(json.dumps(resp.json(), indent=2))
    else:
        print(f"      ❌ Failed: {resp.status_code} - {resp.text}")

def main():
    print("=== Instagram Analytics Backend Test Tool ===")
    
    # 1. Get Token
    token, email = create_test_user()
    
    # 2. Get Code
    code = start_oauth_flow()
    
    if not code:
        print("No code provided. Exiting.")
        return

    # 3. Exchange Code
    user_id = exchange_code(token, code)
    
    # 4. Test Analytics
    if user_id:
        test_analytics_endpoints(token, user_id)

if __name__ == "__main__":
    main()
