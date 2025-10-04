# creator_profile_generator.py - Utility functions to help generate creator profiles

import requests
import json
import random
from typing import List, Dict, Optional
from urllib.parse import urlencode

class CreatorProfileGenerator:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        
    def get_available_niches(self) -> List[Dict]:
        """Get all available niches from the API"""
        try:
            response = requests.get(f"{self.base_url}/niches")
            if response.status_code == 200:
                data = response.json()
                return data.get("data", {}).get("niches", [])
            else:
                print(f"Failed to get niches: {response.status_code}")
                return []
        except Exception as e:
            print(f"Error fetching niches: {e}")
            return []
    
    def generate_profile_url(
        self,
        name: str,
        bio: str,
        followers_count: Optional[int] = None,
        engagement_rate: Optional[float] = None,
        niche_names: Optional[List[str]] = None,
        profile_image: Optional[str] = None
    ) -> str:
        """
        Generate a complete URL for creator profile setup
        
        Args:
            name: Creator name
            bio: Creator bio
            followers_count: Number of followers
            engagement_rate: Engagement rate as float (e.g., 4.5)
            niche_names: List of niche names (will be converted to IDs)
            profile_image: Profile image URL
        
        Returns:
            Complete URL for profile setup
        """
        # Get available niches to convert names to IDs
        available_niches = self.get_available_niches()
        niche_name_to_id = {niche["name"]: niche["id"] for niche in available_niches}
        
        # Convert niche names to IDs
        niche_ids = []
        if niche_names:
            for niche_name in niche_names:
                if niche_name in niche_name_to_id:
                    niche_ids.append(niche_name_to_id[niche_name])
                else:
                    print(f"Warning: Niche '{niche_name}' not found. Available niches:")
                    for available in available_niches:
                        print(f"  - {available['name']}")
        
        # Build query parameters
        params = {"name": name, "bio": bio}
        
        if followers_count is not None:
            params["followers_count"] = followers_count
        if engagement_rate is not None:
            params["engagement_rate"] = engagement_rate
        if niche_ids:
            params["niche_ids"] = ",".join(map(str, niche_ids))
        if profile_image:
            params["profile_image"] = profile_image
        
        # Generate URL
        url = f"{self.base_url}/profile/creator/setup?" + urlencode(params)
        return url
    
    def setup_creator_profile(
        self,
        token: str,
        name: str,
        bio: str,
        followers_count: Optional[int] = None,
        engagement_rate: Optional[float] = None,
        niche_names: Optional[List[str]] = None,
        profile_image: Optional[str] = None
    ) -> Dict:
        """
        Complete function to set up creator profile via API call
        
        Args:
            token: Bearer token for authentication
            name: Creator name
            bio: Creator bio
            followers_count: Number of followers
            engagement_rate: Engagement rate as float (e.g., 4.5)
            niche_names: List of niche names
            profile_image: Profile image URL
        
        Returns:
            API response as dictionary
        """
        url = self.generate_profile_url(
            name=name,
            bio=bio,
            followers_count=followers_count,
            engagement_rate=engagement_rate,
            niche_names=niche_names,
            profile_image=profile_image
        )
        
        headers = {"Authorization": f"Bearer {token}"}
        
        try:
            response = requests.post(url, headers=headers)
            return {
                "status_code": response.status_code,
                "success": response.status_code == 200,
                "data": response.json(),
                "url_used": url
            }
        except Exception as e:
            return {
                "status_code": None,
                "success": False,
                "error": str(e),
                "url_used": url
            }
    
    def generate_random_creator(self, token: str) -> Dict:
        """Generate a random creator profile for testing"""
        
        # Random creator data
        first_names = ["Sarah", "Mike", "Aisha", "David", "Fatima", "John", "Kemi", "James", "Adaora", "Ibrahim"]
        last_names = ["Johnson", "Smith", "Okafor", "Williams", "Adebayo", "Brown", "Uche", "Wilson", "Sanni", "Ahmed"]
        
        niches_pool = ["Beauty", "Tech", "Fashion", "Food", "Travel", "Fitness", "Business", "Gaming", "Music", "Education"]
        
        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        bio = f"Content creator passionate about {random.choice(niches_pool).lower()} and lifestyle. Sharing my journey with you!"
        followers_count = random.randint(10000, 100000)
        engagement_rate = round(random.uniform(2.5, 6.0), 1)
        selected_niches = random.sample(niches_pool, random.randint(2, 4))
        
        return self.setup_creator_profile(
            token=token,
            name=name,
            bio=bio,
            followers_count=followers_count,
            engagement_rate=engagement_rate,
            niche_names=selected_niches
        )
    
    def bulk_create_creators(self, tokens: List[str], count: int = 5) -> List[Dict]:
        """Create multiple random creators for testing"""
        results = []
        
        for i in range(min(count, len(tokens))):
            print(f"Creating creator {i+1}/{count}...")
            result = self.generate_random_creator(tokens[i])
            results.append(result)
            
            if result["success"]:
                creator_name = result["data"].get("data", {}).get("creator", {}).get("name", "Unknown")
                print(f"✅ Created: {creator_name}")
            else:
                print(f"❌ Failed: {result.get('error', 'Unknown error')}")
        
        return results
    
    def display_available_niches(self):
        """Display all available niches in a readable format"""
        niches = self.get_available_niches()
        
        if not niches:
            print("No niches available or failed to fetch")
            return
        
        print(f"\n📋 Available Niches ({len(niches)}):")
        print("=" * 50)
        
        for i, niche in enumerate(niches, 1):
            print(f"{i:2d}. {niche['name']} (ID: {niche['id']})")
        
        print("=" * 50)
        return niches


# Example usage functions
def create_sample_creator():
    """Example: Create a single creator profile"""
    generator = CreatorProfileGenerator()
    
    # Your creator token (get this from login)
    token = "your_creator_jwt_token_here"
    
    result = generator.setup_creator_profile(
        token=token,
        name="Beauty Sarah",
        bio="Nigerian beauty influencer sharing skincare tips and makeup tutorials",
        followers_count=45000,
        engagement_rate=4.8,
        niche_names=["Beauty", "Skincare", "Fashion", "Lifestyle"]
    )
    
    print(json.dumps(result, indent=2))
    return result

def create_multiple_creators():
    """Example: Create multiple creators"""
    generator = CreatorProfileGenerator()
    
    # List of creator tokens
    tokens = [
        "creator_token_1",
        "creator_token_2", 
        "creator_token_3"
    ]
    
    results = generator.bulk_create_creators(tokens, count=3)
    
    print(f"\nCreated {len(results)} creators:")
    for i, result in enumerate(results, 1):
        print(f"{i}. Success: {result['success']}")

def show_niches():
    """Example: Display available niches"""
    generator = CreatorProfileGenerator()
    generator.display_available_niches()

def generate_url_only():
    """Example: Just generate the URL without making the API call"""
    generator = CreatorProfileGenerator()
    
    url = generator.generate_profile_url(
        name="Test Creator",
        bio="This is a test bio",
        followers_count=25000,
        engagement_rate=3.7,
        niche_names=["Tech", "Gaming"]
    )
    
    print("Generated URL:")
    print(url)
    return url

# CLI-like interface
if __name__ == "__main__":
    import sys
    
    generator = CreatorProfileGenerator()
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python creator_profile_generator.py niches              # Show available niches")
        print("  python creator_profile_generator.py create <token>      # Create random creator")
        print("  python creator_profile_generator.py url                 # Generate sample URL")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "niches":
        generator.display_available_niches()
    
    elif command == "create" and len(sys.argv) > 2:
        token = sys.argv[2]
        result = generator.generate_random_creator(token)
        print(json.dumps(result, indent=2))
    
    elif command == "url":
        url = generate_url_only()
    
    else:
        print("Invalid command or missing token")