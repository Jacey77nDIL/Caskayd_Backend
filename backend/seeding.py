# simple_seed_data.py - Using direct SQL to avoid relationship issues

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

from auth import hash_password

load_dotenv()

# Get database URL and convert to asyncpg format
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL.startswith("postgresql+asyncpg://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

# Industry to Niche mappings
INDUSTRY_NICHE_MAPPING = {
    "Beauty & Cosmetics": ["Beauty", "Skincare", "Makeup", "Fashion"],
    "Fashion & Apparel": ["Fashion", "Lifestyle", "Beauty", "Style"],
    "Technology": ["Tech", "Gaming", "Lifestyle", "Education"],
    "Food & Beverage": ["Food", "Lifestyle", "Health", "Cooking"],
    "Health & Wellness": ["Health", "Fitness", "Lifestyle", "Wellness"],
    "Travel & Tourism": ["Travel", "Lifestyle", "Photography", "Adventure"],
    "Entertainment": ["Entertainment", "Gaming", "Lifestyle", "Music"],
    "Sports & Recreation": ["Sports", "Fitness", "Lifestyle", "Health"],
    "Home & Garden": ["Home Decor", "Lifestyle", "DIY", "Gardening"],
    "Finance & Investment": ["Finance", "Business", "Education", "Lifestyle"],
    "Education & Training": ["Education", "Tech", "Business", "Lifestyle"],
    "Automotive": ["Automotive", "Tech", "Lifestyle", "Reviews"],
    "Pet Care": ["Pets", "Lifestyle", "Health", "Family"],
    "Parenting & Family": ["Parenting", "Family", "Lifestyle", "Education"],
    "Real Estate": ["Real Estate", "Business", "Lifestyle", "Investment"]
}

async def create_tables(conn):
    """Create all necessary tables"""
    print("📝 Creating tables...")
    
    # Create niches table
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS niches (
            id SERIAL PRIMARY KEY,
            name VARCHAR UNIQUE NOT NULL
        );
    """)
    
    # Create industries table
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS industries (
            id SERIAL PRIMARY KEY,
            name VARCHAR UNIQUE NOT NULL
        );
    """)
    
    # Create association tables
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS creator_niches (
            creator_id INTEGER REFERENCES users_creators(id) ON DELETE CASCADE,
            niche_id INTEGER REFERENCES niches(id) ON DELETE CASCADE,
            PRIMARY KEY (creator_id, niche_id)
        );
    """)
    
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS business_industries (
            business_id INTEGER REFERENCES users_businesses(id) ON DELETE CASCADE,
            industry_id INTEGER REFERENCES industries(id) ON DELETE CASCADE,
            PRIMARY KEY (business_id, industry_id)
        );
    """)
    
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS industry_niches (
            industry_id INTEGER REFERENCES industries(id) ON DELETE CASCADE,
            niche_id INTEGER REFERENCES niches(id) ON DELETE CASCADE,
            PRIMARY KEY (industry_id, niche_id)
        );
    """)
    
    # Create interaction tracking table
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS business_creator_interactions (
            id SERIAL PRIMARY KEY,
            business_id INTEGER REFERENCES users_businesses(id) ON DELETE CASCADE,
            creator_id INTEGER REFERENCES users_creators(id) ON DELETE CASCADE,
            viewed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            interaction_type VARCHAR DEFAULT 'viewed'
        );
    """)
    
    # Create cache table
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS recommendation_cache (
            id SERIAL PRIMARY KEY,
            business_id INTEGER REFERENCES users_businesses(id) ON DELETE CASCADE,
            cache_key VARCHAR NOT NULL,
            creator_ids TEXT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            expires_at TIMESTAMP WITH TIME ZONE,
            last_accessed TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    """)
    
    print("✅ Tables created successfully!")

async def seed_niches_and_industries(conn):
    """Seed niches and industries using direct SQL"""
    print("📝 Seeding niches and industries...")
    
    # Get all unique niches
    all_niches = set()
    for niches in INDUSTRY_NICHE_MAPPING.values():
        all_niches.update(niches)
    
    # Insert niches - check existence first
    for niche_name in sorted(all_niches):
        existing = await conn.fetchval("SELECT id FROM niches WHERE name = $1", niche_name)
        if not existing:
            await conn.execute("INSERT INTO niches (name) VALUES ($1)", niche_name)
    
    print(f"✅ Inserted {len(all_niches)} niches")
    
    # Insert industries - check existence first
    for industry_name in INDUSTRY_NICHE_MAPPING.keys():
        existing = await conn.fetchval("SELECT id FROM industries WHERE name = $1", industry_name)
        if not existing:
            await conn.execute("INSERT INTO industries (name) VALUES ($1)", industry_name)
    
    print(f"✅ Inserted {len(INDUSTRY_NICHE_MAPPING)} industries")
    
    # Create industry-niche relationships
    for industry_name, niche_names in INDUSTRY_NICHE_MAPPING.items():
        for niche_name in niche_names:
            # Check if relationship already exists
            existing = await conn.fetchval("""
                SELECT 1 FROM industry_niches in_n
                JOIN industries i ON i.id = in_n.industry_id
                JOIN niches n ON n.id = in_n.niche_id
                WHERE i.name = $1 AND n.name = $2
            """, industry_name, niche_name)
            
            if not existing:
                await conn.execute("""
                    INSERT INTO industry_niches (industry_id, niche_id)
                    SELECT i.id, n.id
                    FROM industries i, niches n
                    WHERE i.name = $1 AND n.name = $2
                """, industry_name, niche_name)
    
    print("✅ Industry-niche relationships created!")

async def add_sample_creators(conn):
    """Add sample creators with Instagram data"""
    print("📝 Adding sample creators...")
    
    sample_creators = [
        {
            "name": "Sarah Beauty",
            "email": "sarah.beauty@example.com",
            "bio": "Beauty and lifestyle content creator passionate about skincare and wellness",
            "niches": ["Beauty", "Skincare", "Lifestyle"],
            "instagram": {
                "username": "sarahbeauty_ng",
                "followers_count": 50000,
                "engagement_rate": 4.2,
                "reach_7d": 35000
            }
        },
        {
            "name": "Tech Mike",
            "email": "techmike@example.com",
            "bio": "Tech reviewer and gadget enthusiast. Breaking down the latest tech for everyone",
            "niches": ["Tech", "Gaming", "Education"],
            "instagram": {
                "username": "techmike_reviews",
                "followers_count": 75000,
                "engagement_rate": 3.8,
                "reach_7d": 45000
            }
        },
        {
            "name": "Fitness Queen",
            "email": "fitnessqueen@example.com",
            "bio": "Personal trainer helping you achieve your fitness goals. Health is wealth!",
            "niches": ["Fitness", "Health", "Wellness"],
            "instagram": {
                "username": "fitness_queen_ng",
                "followers_count": 35000,
                "engagement_rate": 5.1,
                "reach_7d": 28000
            }
        },
        {
            "name": "Foodie Adventures",
            "email": "foodieadv@example.com",
            "bio": "Exploring Nigerian cuisine and sharing amazing recipes with food lovers worldwide",
            "niches": ["Food", "Cooking", "Lifestyle"],
            "instagram": {
                "username": "foodie_adventures_ng",
                "followers_count": 42000,
                "engagement_rate": 4.7,
                "reach_7d": 31000
            }
        },
        {
            "name": "Travel Nomad",
            "email": "travelnomad@example.com",
            "bio": "Capturing beautiful moments across Africa. Adventure awaits at every corner!",
            "niches": ["Travel", "Photography", "Adventure"],
            "instagram": {
                "username": "travel_nomad_africa",
                "followers_count": 68000,
                "engagement_rate": 3.9,
                "reach_7d": 52000
            }
        },
        {
            "name": "Fashion Forward",
            "email": "fashionforward@example.com",
            "bio": "African fashion enthusiast showcasing the latest trends and timeless styles",
            "niches": ["Fashion", "Style", "Lifestyle"],
            "instagram": {
                "username": "fashion_forward_africa",
                "followers_count": 89000,
                "engagement_rate": 4.3,
                "reach_7d": 67000
            }
        },
        {
            "name": "Home Decor Pro",
            "email": "homedecor@example.com",
            "bio": "Interior design tips and home decoration ideas for modern African homes",
            "niches": ["Home Decor", "DIY", "Lifestyle"],
            "instagram": {
                "username": "home_decor_pro_ng",
                "followers_count": 23000,
                "engagement_rate": 6.2,
                "reach_7d": 18000
            }
        },
        {
            "name": "Business Guru",
            "email": "bizguru@example.com",
            "bio": "Entrepreneur and business coach helping others build successful ventures",
            "niches": ["Business", "Education", "Finance"],
            "instagram": {
                "username": "business_guru_ng",
                "followers_count": 54000,
                "engagement_rate": 3.6,
                "reach_7d": 41000
            }
        }
    ]
    
    for creator_data in sample_creators:
        # Check if creator already exists
        existing = await conn.fetchval("""
            SELECT id FROM users_creators WHERE email = $1
        """, creator_data["email"])
        
        if existing:
            print(f"⏭️ Creator {creator_data['name']} already exists, skipping...")
            continue
        
        # Insert creator
        creator_id = await conn.fetchval("""
            INSERT INTO users_creators (category, email, name, bio, password_hash, created_at)
            VALUES ($1, $2, $3, $4, $5, NOW())
            RETURNING id
        """, "creator", creator_data["email"], creator_data["name"], 
             creator_data["bio"], hash_password("password123"))
        
        # Insert Instagram social data
        instagram = creator_data["instagram"]
        await conn.execute("""
            INSERT INTO instagram_creator_socials 
            (user_id, platform, instagram_username, followers_count, engagement_rate, reach_7d, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, NOW())
        """, creator_id, "instagram", instagram["username"], 
             instagram["followers_count"], instagram["engagement_rate"], instagram["reach_7d"])
        
        # Link creator to niches
        for niche_name in creator_data["niches"]:
            # Check if relationship already exists
            existing = await conn.fetchval("""
                SELECT 1 FROM creator_niches cn
                JOIN niches n ON n.id = cn.niche_id
                WHERE cn.creator_id = $1 AND n.name = $2
            """, creator_id, niche_name)
            
            if not existing:
                await conn.execute("""
                    INSERT INTO creator_niches (creator_id, niche_id)
                    SELECT $1, n.id
                    FROM niches n
                    WHERE n.name = $2
                """, creator_id, niche_name)
        
        print(f"✅ Added creator: {creator_data['name']} (@{instagram['username']})")
    
    print("✅ All sample creators added!")

async def main():
    """Main function"""
    print("🚀 Starting database setup with direct SQL...")
    
    try:
        # Connect to database
        conn = await asyncpg.connect(DATABASE_URL)
        
        # Step 1: Create tables
        await create_tables(conn)
        
        # Step 2: Seed industries and niches
        await seed_niches_and_industries(conn)
        
        # Step 3: Add sample creators
        await add_sample_creators(conn)
        
        
        await conn.close()
        
    except Exception as e:
        print(f"💥 Setup failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())