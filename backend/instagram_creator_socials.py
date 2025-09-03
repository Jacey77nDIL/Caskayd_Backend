import os
import time
import math
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, Dict, Any, List

import jwt  # PyJWT
import requests
from sqlalchemy import (
    Column, Integer, BigInteger, String, Float, DateTime, ForeignKey, Index,
    UniqueConstraint, Text, func, select, and_, update
)
from sqlalchemy.orm import declarative_base, relationship, Session
from models import InstagramCreatorSocial

# ---------------------------
# Settings / Env
# ---------------------------
FB_APP_ID = os.getenv("FB_APP_ID", "")
FB_APP_SECRET = os.getenv("FB_APP_SECRET")
REDIRECT_URI = os.getenv("FACEBOOK_REDIRECT_URI")

JWT_ALGORITHM = os.getenv("ALGORITHM")
JWT_SECRET = os.getenv("SECRET_KEY")  # used if algorithm is HS256

if not FB_APP_ID or not FB_APP_SECRET or not REDIRECT_URI:
    logging.warning("Facebook env variables are not fully set.")

# ---------------------------
# JWT helpers
# ---------------------------
def decode_user_id_from_jwt(authorization_header: str) -> int:
    """
    Expects 'Authorization: Bearer <jwt>'.
    Returns internal user_id from JWT claims (sub or user_id).
    """
    if not authorization_header or not authorization_header.lower().startswith("bearer "):
        raise ValueError("Missing or invalid Authorization header.")

    token = authorization_header.split(" ", 1)[1].strip()
    try:
        claims = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM], options={"verify_aud": False})
    except Exception as e:
        raise ValueError(f"Invalid JWT: {e}")

    # Adjust to your frontend’s JWT claim names
    user_id = claims.get("sub") or claims.get("user_id") or claims.get("id")
    if not user_id:
        raise ValueError("JWT missing user identifier (sub/user_id/id).")
    return int(user_id)

# ---------------------------
# Facebook / Instagram Graph helpers
# ---------------------------
FB_GRAPH = "https://graph.facebook.com/v19.0"

def _exchange_code_for_short_token(code: str) -> Dict[str, Any]:
    res = requests.get(
        f"{FB_GRAPH}/oauth/access_token",
        params={
            "client_id": FB_APP_ID,
            "client_secret": FB_APP_SECRET,
            "redirect_uri": REDIRECT_URI,
            "code": code,
        },
        timeout=30,
    )
    data = res.json()
    if res.status_code != 200 or "access_token" not in data:
        raise RuntimeError(f"Failed short-lived token exchange: {data}")
    return data

def _exchange_for_long_token(token: str) -> Dict[str, Any]:
    res = requests.get(
        f"{FB_GRAPH}/oauth/access_token",
        params={
            "grant_type": "fb_exchange_token",
            "client_id": FB_APP_ID,
            "client_secret": FB_APP_SECRET,
            "fb_exchange_token": token,
        },
        timeout=30,
    )
    data = res.json()
    if res.status_code != 200 or "access_token" not in data:
        raise RuntimeError(f"Failed long-lived token exchange: {data}")
    return data

def _find_instagram_user(token: str) -> Tuple[str, Optional[str], Optional[str]]:
    """
    Returns (ig_user_id, page_id, page_name)
    Strategy:
      1) /me/accounts -> list pages
      2) For each page -> ?fields=instagram_business_account,id,name
      3) Return first page that has instagram_business_account.id
    """
    pages = requests.get(
        f"{FB_GRAPH}/me/accounts",
        params={"access_token": token, "limit": 50},
        timeout=30,
    ).json()

    if "data" not in pages:
        raise RuntimeError(f"Unable to list pages: {pages}")

    for pg in pages["data"]:
        pid = pg.get("id")
        pinfo = requests.get(
            f"{FB_GRAPH}/{pid}",
            params={"fields": "instagram_business_account,name", "access_token": token},
            timeout=30,
        ).json()
        igba = pinfo.get("instagram_business_account", {})
        ig_user_id = igba.get("id")
        if ig_user_id:
            return ig_user_id, pid, pinfo.get("name")

    raise RuntimeError("No connected Instagram Business Account found on any page.")

def _get_followers_and_username(ig_user_id: str, token: str) -> Tuple[Optional[int], Optional[str]]:
    r = requests.get(
        f"{FB_GRAPH}/{ig_user_id}",
        params={"fields": "followers_count,username", "access_token": token},
        timeout=30,
    ).json()
    return r.get("followers_count"), r.get("username")

def _reach_7d(ig_user_id: str, token: str) -> Optional[int]:
    # Sum last 7 daily values of reach
    r = requests.get(
        f"{FB_GRAPH}/{ig_user_id}/insights",
        params={"metric": "reach", "period": "day", "access_token": token},
        timeout=30,
    ).json()
    try:
        values = r["data"][0]["values"]  # [{end_time:..., value:int}, ...]
    except Exception:
        return None
    # take last 7 values
    vals = [v.get("value", 0) for v in values][-7:]
    return int(sum(v for v in vals if isinstance(v, (int, float))))

def _engagement_rate(ig_user_id: str, token: str, followers: Optional[int]) -> Optional[float]:
    """
    Approx engagement rate = (sum(like_count + comments_count) over last N posts) / followers * 100
    Using last 20 media (adjust as you wish).
    """
    if not followers or followers <= 0:
        return None

    total_interactions = 0
    after = None
    fetched = 0
    N = 20

    while fetched < N:
        params = {
            "fields": "like_count,comments_count",
            "limit": min(25, N - fetched),
            "access_token": token,
        }
        if after:
            params["after"] = after
        r = requests.get(f"{FB_GRAPH}/{ig_user_id}/media", params=params, timeout=30).json()
        data = r.get("data", [])
        for m in data:
            likes = m.get("like_count") or 0
            comments = m.get("comments_count") or 0
            total_interactions += (likes + comments)
        fetched += len(data)
        after = (r.get("paging") or {}).get("cursors", {}).get("after")
        if not after or not data:
            break

    if fetched == 0:
        return None

    er = (total_interactions / float(followers)) * 100.0
    # Round to 2 decimals for reporting
    return round(er, 2)

# ---------------------------
# Public API: main action called by your endpoint
# ---------------------------
def exchange_token_and_upsert_insights(db: Session, code: str, authorization_header: str) -> Dict[str, Any]:
    """
    - Validates JWT, gets user_id
    - code -> short token -> long token
    - find IG user id
    - pull followers, reach_7d, engagement_rate
    - upsert row in creator_socials
    - return a compact payload for the frontend
    """
    user_id = decode_user_id_from_jwt(authorization_header)

    short_data = _exchange_code_for_short_token(code)
    short_token = short_data["access_token"]

    long_data = _exchange_for_long_token(short_token)
    long_token = long_data["access_token"]
    token_updated_at = datetime.now(timezone.utc)

    ig_user_id, page_id, page_name = _find_instagram_user(long_token)

    followers, ig_username = _get_followers_and_username(ig_user_id, long_token)
    reach7 = _reach_7d(ig_user_id, long_token)
    er = _engagement_rate(ig_user_id, long_token, followers)

    insights_updated_at = datetime.now(timezone.utc)

    # Upsert (by user_id + platform)
    existing: Optional[InstagramCreatorSocial] = db.execute(
        select(InstagramCreatorSocial).where(
            and_(InstagramCreatorSocial.user_id == user_id, InstagramCreatorSocial.platform == "instagram")
        )
    ).scalar_one_or_none()

    if existing:
        existing.facebook_page_id = page_id
        existing.facebook_page_name = page_name
        existing.instagram_user_id = ig_user_id
        existing.instagram_username = ig_username
        existing.followers_count = followers
        existing.reach_7d = reach7
        existing.engagement_rate = er
        existing.long_lived_token = long_token
        existing.token_last_updated_at = token_updated_at
        existing.insights_last_updated_at = insights_updated_at
    else:
        cs = InstagramCreatorSocial(
            user_id=user_id,
            platform="instagram",
            facebook_page_id=page_id,
            facebook_page_name=page_name,
            instagram_user_id=ig_user_id,
            instagram_username=ig_username,
            followers_count=followers,
            reach_7d=reach7,
            engagement_rate=er,
            long_lived_token=long_token,
            token_last_updated_at=token_updated_at,
            insights_last_updated_at=insights_updated_at,
        )
        db.add(cs)

    db.commit()

    return {
        "user_id": user_id,
        "platform": "instagram",
        "instagram_user_id": ig_user_id,
        "instagram_username": ig_username,
        "followers": followers,
        "reach_7d": reach7,
        "engagement_rate": er,
        "token_last_updated_at": token_updated_at.isoformat(),
        "insights_last_updated_at": insights_updated_at.isoformat(),
    }

# ---------------------------
# Worker-facing helpers
# ---------------------------
def refresh_insights_for_row(db: Session, row: InstagramCreatorSocial) -> None:
    token = row.long_lived_token
    if not token or not row.instagram_user_id:
        return
    followers, ig_username = _get_followers_and_username(row.instagram_user_id, token)
    reach7 = _reach_7d(row.instagram_user_id, token)
    er = _engagement_rate(row.instagram_user_id, token, followers)

    row.instagram_username = ig_username or row.instagram_username
    row.followers_count = followers
    row.reach_7d = reach7
    row.engagement_rate = er
    row.insights_last_updated_at = datetime.now(timezone.utc)
    db.commit()

def refresh_long_lived_token_for_row(db: Session, row: InstagramCreatorSocial) -> None:
    token = row.long_lived_token
    if not token:
        return
    data = _exchange_for_long_token(token)
    row.long_lived_token = data["access_token"]
    row.token_last_updated_at = datetime.now(timezone.utc)
    db.commit()
