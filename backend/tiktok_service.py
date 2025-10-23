import os
import httpx
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_

from models import TikTokCreatorSocial, UserCreator

# Get TikTok App credentials from environment
TIKTOK_CLIENT_KEY = os.getenv("TIKTOK_CLIENT_KEY")
TIKTOK_CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET")
# This MUST match the one in your TikTok App dashboard
TIKTOK_REDIRECT_URI = os.getenv("TIKTOK_REDIRECT_URI") 

AUTH_BASE_URL = "https://www.tiktok.com/v2/auth/authorize/"
API_BASE_URL = "https://open.tiktokapis.com/v2/"

logger = logging.getLogger(__name__)

class TikTokService:
    
    def get_authorization_url(self, state: str) -> str:
        """
        Generates the URL to redirect the user to for TikTok login.
        """
        if not TIKTOK_CLIENT_KEY or not TIKTOK_REDIRECT_URI:
            logger.error("TikTok env vars (KEY, REDIRECT_URI) not set")
            raise ValueError("TikTok service is not configured.")
            
        # Scopes required to get profile info and follower counts
        scopes = "user.info.basic" 
        
        params = {
            "client_key": TIKTOK_CLIENT_KEY,
            "response_type": "code",
            "scope": scopes,
            "redirect_uri": TIKTOK_REDIRECT_URI,
            "state": state,
        }
        query_string = httpx.URL(url="").copy_with(params=params).query.decode("utf-8")
        return f"{AUTH_BASE_URL}?{query_string}"

    async def _exchange_code_for_token(self, code: str) -> dict:
        """
        Internal: Exchanges the authorization code for an access token.
        """
        if not TIKTOK_CLIENT_KEY or not TIKTOK_CLIENT_SECRET or not TIKTOK_REDIRECT_URI:
            raise ValueError("TikTok service is not configured.")
            
        url = f"{API_BASE_URL}oauth/token/"
        data = {
            "client_key": TIKTOK_CLIENT_KEY,
            "client_secret": TIKTOK_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": TIKTOK_REDIRECT_URI,
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, data=data)
                response.raise_for_status() # Raise exception for 4xx/5xx
                token_data = response.json()
                
                if "error" in token_data:
                    logger.error(f"TikTok token exchange error: {token_data}")
                    raise ValueError(token_data.get("error_description", "Token exchange failed"))
                
                return token_data
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error during token exchange: {e.response.text}")
                raise
            except Exception as e:
                logger.error(f"Error during token exchange: {e}")
                raise

    async def _get_user_info(self, access_token: str) -> dict:
        """
        Internal: Fetches user info from TikTok using an access token.
        """
        url = f"{API_BASE_URL}user/info/"
        
        # Define the fields you want
        fields = "open_id,union_id,display_name,avatar_large_url,follower_count,likes_count,video_count"
        
        headers = {"Authorization": f"Bearer {access_token}"}
        params = {"fields": fields}
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, params=params)
                response.raise_for_status()
                user_data = response.json()

                if "error" in user_data and user_data["error"]["code"] != "ok":
                    logger.error(f"TikTok user info error: {user_data}")
                    raise ValueError(user_data.get("error", {}).get("message", "Failed to get user info"))
                
                return user_data.get("data", {}).get("user", {})
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error during user info fetch: {e.response.text}")
                raise
            except Exception as e:
                logger.error(f"Error during user info fetch: {e}")
                raise

    async def exchange_code_and_upsert_data(
        self, 
        db: AsyncSession, 
        code: str, 
        creator_user_id: int
    ) -> dict:
        """
        Main service function:
        1. Exchanges code for token.
        2. Fetches user info.
        3. Upserts data into TikTokCreatorSocial table.
        """
        
        # 1. Exchange code for token
        token_data = await self._exchange_code_for_token(code)
        
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 0)
        refresh_expires_in = token_data.get("refresh_expires_in", 0)
        
        now = datetime.now(timezone.utc)
        token_expires_at = now + timedelta(seconds=expires_in)
        refresh_token_expires_at = now + timedelta(seconds=refresh_expires_in)
        
        # 2. Fetch user info
        user_info = await self._get_user_info(access_token)
        
        # 3. Upsert data
        existing_result = await db.execute(
            select(TikTokCreatorSocial).where(and_(
                TikTokCreatorSocial.user_id == creator_user_id,
                TikTokCreatorSocial.platform == "tiktok"
            ))
        )
        existing = existing_result.scalar_one_or_none()
        
        if existing:
            # Update existing record
            social = existing
        else:
            # Create new record
            social = TikTokCreatorSocial(
                user_id=creator_user_id,
                platform="tiktok"
            )
            db.add(social)

        # Update all fields
        social.open_id = user_info.get("open_id")
        social.union_id = user_info.get("union_id")
        social.display_name = user_info.get("display_name")
        social.profile_image_url = user_info.get("avatar_large_url")
        social.followers_count = user_info.get("follower_count")
        social.likes_count = user_info.get("likes_count")
        social.video_count = user_info.get("video_count")
        
        social.access_token = access_token
        social.refresh_token = refresh_token
        social.token_expires_at = token_expires_at
        social.refresh_token_expires_at = refresh_token_expires_at
        
        social.token_last_updated_at = now
        social.insights_last_updated_at = now
        
        await db.commit()
        await db.refresh(social)
        
        return {
            "status": "success",
            "tiktok_username": social.display_name,
            "followers": social.followers_count,
            "likes": social.likes_count,
        }

# Global instance
tiktok_service = TikTokService()