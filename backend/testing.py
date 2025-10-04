# swagger_test.py - Test using the exact Swagger UI format

import requests
import json

BASE_URL = "http://localhost:8000"

def test_with_swagger_format():
    print("Testing with Swagger UI format...\n")
    
    # Your creator token
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJzYXJhaC5iZWF1dHlAZXhhbXBsZS5jb20iLCJyb2xlIjoiY3JlYXRvciJ9.Y2syQg5t_1A5a3socEfu2iATOOSpC4GxD8K5X6coJyQ"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Test 1: Basic profile setup
    print("1. Testing basic profile setup...")
    
    params = {
        "name": "Sarah Beauty Test",
        "bio": "Beauty content creator testing profile setup",
        "followers_count": 25000,
        "engagement_rate": 4.5,
        "niche_ids": "3,19"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/profile/creator/setup",
            params=params,
            headers=headers
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}\n")
        
        if response.status_code == 200:
            print("✅ Profile setup successful!")
        else:
            print("❌ Profile setup failed")
            if response.status_code == 422:
                print("Validation error - check parameter format")
    
    except Exception as e:
        print(f"Request failed: {e}")
    
    # Test 2: Try with different tokens
    print("\n2. Testing with different creator tokens...")
    
    tokens_to_test = [
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZWNobWlrZUBleGFtcGxlLmNvbSIsInJvbGUiOiJjcmVhdG9yIn0.zr-QI836xHv9YC6vLt3U6xnoHIiWXNs3HGhEdlOCLjk",
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJmaXRuZXNzcXVlZW5AZXhhbXBsZS5jb20iLCJyb2xlIjoiY3JlYXRvciJ9.nr2OxEgr-p5SHx5LqRAoO_lcIjJ5rHSFiucMH3lto14"
    ]
    
    for i, test_token in enumerate(tokens_to_test, 1):
        print(f"\nTesting token {i}...")
        
        headers["Authorization"] = f"Bearer {test_token}"
        
        params = {
            "name": f"Test Creator {i}",
            "bio": f"Test bio for creator {i}",
            "followers_count": 15000 + (i * 5000),
            "engagement_rate": 3.5 + (i * 0.5),
            "niche_ids": "30,19" if i == 1 else "12,16,19"  # Tech/Lifestyle or Fitness/Health/Lifestyle
        }
        
        try:
            response = requests.post(
                f"{BASE_URL}/profile/creator/setup",
                params=params,
                headers=headers
            )
            
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print("   ✅ Success!")
            else:
                print(f"   ❌ Failed: {response.text[:100]}")
                
        except Exception as e:
            print(f"   Request failed: {e}")

def test_swagger_ui_directly():
    """Instructions for testing directly in Swagger UI"""
    print("\n=== TESTING IN SWAGGER UI ===")
    print("1. Go to http://127.0.0.1:8000/docs#/default/setup_creator_profile_profile_creator_setup_post")
    print("\n2. Click 'Try it out' button")
    print("\n3. Fill in these values:")
    print("   name: Sarah Beauty")
    print("   bio: Beauty and lifestyle content creator")
    print("   followers_count: 25000")
    print("   engagement_rate: 4.5")
    print("   niche_ids: 3,19")
    print("\n4. Click the lock icon and enter your Bearer token:")
    print("   eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJzYXJhaC5iZWF1dHlAZXhhbXBsZS5jb20iLCJyb2xlIjoiY3JlYXRvciJ9.Y2syQg5t_1A5a3socEfu2iATOOSpC4GxD8K5X6coJyQ")
    print("\n5. Click Execute")

def bulk_test_creators():
    """Test multiple creators quickly"""
    print("\n=== BULK CREATOR TEST ===")
    
    test_data = [
        {
            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJzYXJhaC5iZWF1dHlAZXhhbXBsZS5jb20iLCJyb2xlIjoiY3JlYXRvciJ9.Y2syQg5t_1A5a3socEfu2iATOOSpC4GxD8K5X6coJyQ",
            "name": "Sarah Beauty",
            "bio": "Beauty and lifestyle content creator",
            "followers_count": 50000,
            "engagement_rate": 4.8,
            "niche_ids": "3,27,20"  # Beauty, Skincare, Makeup
        },
        {
            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZWNobWlrZUBleGFtcGxlLmNvbSIsInJvbGUiOiJjcmVhdG9yIn0.zr-QI836xHv9YC6vLt3U6xnoHIiWXNs3HGhEdlOCLjk",
            "name": "Tech Mike",
            "bio": "Tech reviewer and gadget enthusiast",
            "followers_count": 75000,
            "engagement_rate": 3.8,
            "niche_ids": "30,14,7"  # Tech, Gaming, Education
        },
        {
            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJmaXRuZXNzcXVlZW5AZXhhbXBsZS5jb20iLCJyb2xlIjoiY3JlYXRvciJ9.nr2OxEgr-p5SHx5LqRAoO_lcIjJ5rHSFiucMH3lto14",
            "name": "Fitness Queen",
            "bio": "Personal trainer and fitness coach",
            "followers_count": 42000,
            "engagement_rate": 5.2,
            "niche_ids": "12,16,32"  # Fitness, Health, Wellness
        }
    ]
    
    success_count = 0
    
    for i, data in enumerate(test_data, 1):
        print(f"\n{i}. Testing {data['name']}...")
        
        headers = {"Authorization": f"Bearer {data['token']}"}
        params = {k: v for k, v in data.items() if k != 'token'}
        
        try:
            response = requests.post(
                f"{BASE_URL}/profile/creator/setup",
                params=params,
                headers=headers
            )
            
            if response.status_code == 200:
                print(f"   ✅ {data['name']} - SUCCESS")
                success_count += 1
            else:
                print(f"   ❌ {data['name']} - FAILED ({response.status_code})")
                print(f"      Error: {response.text[:150]}")
                
        except Exception as e:
            print(f"   ❌ {data['name']} - ERROR: {e}")
    
    print(f"\n📊 Results: {success_count}/{len(test_data)} creators set up successfully")

if __name__ == "__main__":
    test_with_swagger_format()
    test_swagger_ui_directly()
    bulk_test_creators()