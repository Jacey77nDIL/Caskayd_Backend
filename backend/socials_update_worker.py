import os
import time
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from instagram_creator_socials import InstagramCreatorSocial, refresh_insights_for_row, refresh_long_lived_token_for_row
from models import Base
logging.basicConfig(level=logging.INFO)

DATABASE_URL = os.getenv("DATABASE_URL")
BATCH_SIZE = int(os.getenv("SOCIALS_BATCH_SIZE", "200"))      # tune based on capacity
SLEEP_SECONDS = int(os.getenv("SOCIALS_WORKER_SLEEP", "120")) # loop sleep between passes

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

INSIGHTS_INTERVAL = timedelta(days=7)
TOKEN_INTERVAL = timedelta(days=50)

def _now():
    return datetime.now(timezone.utc)

def process_due_insights(db: Session):
    now = _now()
    cutoff = now - INSIGHTS_INTERVAL

    # Select in batches using SKIP LOCKED (Postgres) to avoid contention
    rows = db.execute(
        text("""
            SELECT id
            FROM creator_socials
            WHERE platform = 'instagram'
              AND (insights_last_updated_at IS NULL OR insights_last_updated_at < :cutoff)
            ORDER BY COALESCE(insights_last_updated_at, to_timestamp(0)) ASC
            LIMIT :batch
            FOR UPDATE SKIP LOCKED
        """),
        {"cutoff": cutoff, "batch": BATCH_SIZE},
    ).fetchall()

    if not rows:
        return 0

    processed = 0
    for (row_id,) in rows:
        cs: InstagramCreatorSocial = db.get(InstagramCreatorSocial, row_id)
        if cs:
            try:
                refresh_insights_for_row(db, cs)
                processed += 1
            except Exception as e:
                logging.exception(f"Failed insights refresh for row {row_id}: {e}")
                db.rollback()
    return processed

def process_due_tokens(db: Session):
    now = _now()
    cutoff = now - TOKEN_INTERVAL

    rows = db.execute(
        text("""
            SELECT id
            FROM creator_socials
            WHERE platform = 'instagram'
              AND (token_last_updated_at IS NULL OR token_last_updated_at < :cutoff)
            ORDER BY COALESCE(token_last_updated_at, to_timestamp(0)) ASC
            LIMIT :batch
            FOR UPDATE SKIP LOCKED
        """),
        {"cutoff": cutoff, "batch": BATCH_SIZE},
    ).fetchall()

    if not rows:
        return 0

    processed = 0
    for (row_id,) in rows:
        cs: InstagramCreatorSocial = db.get(InstagramCreatorSocial, row_id)
        if cs:
            try:
                refresh_long_lived_token_for_row(db, cs)
                processed += 1
            except Exception as e:
                logging.exception(f"Failed token refresh for row {row_id}: {e}")
                db.rollback()
    return processed

def main_loop():
    while True:
        with SessionLocal() as db:
            try:
                n1 = process_due_insights(db)
                n2 = process_due_tokens(db)
                logging.info(f"Processed insights: {n1}, tokens: {n2}")
            except Exception as e:
                logging.exception(f"Worker loop error: {e}")
        time.sleep(SLEEP_SECONDS)

if __name__ == "__main__":
    main_loop()
