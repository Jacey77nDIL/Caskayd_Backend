import requests
import json

# Test the niches endpoint first
print("Testing /niches endpoint...")
response = requests.get("http://localhost:8000/niches")
print(f"Status: {response.status_code}")
print(f"Response: {response.text[:200]}")

if response.status_code == 200:
    niches = response.json()["data"]["niches"]
    print(f"Found {len(niches)} niches")
    
    # Test profile setup with one token
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJzYXJhaC5iZWF1dHlAZXhhbXBsZS5jb20iLCJyb2xlIjoiY3JlYXRvciJ9.Y2syQg5t_1A5a3socEfu2iATOOSpC4GxD8K5X6coJyQ"
    
    url = "http://localhost:8000/profile/creator/setup"
    params = {
        "name": "Sarah Test",
        "bio": "Test bio",
        "followers_count": 25000,
        "engagement_rate": 4.5,
        "niche_ids": "3,19"  # Beauty and Lifestyle
    }
    
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\nTesting profile setup...")
    response = requests.post(url, params=params, headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")