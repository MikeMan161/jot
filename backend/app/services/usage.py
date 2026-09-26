"""
Per-user, per-day counting for the paid AI endpoint.

This is the cap that actually bounds the Anthropic bill. The in-memory burst limiter
in app/limiter.py stops someone hammering the endpoint for a minute, but its counters
die with the process, so a redeploy hands everyone a fresh allowance. A row in
Postgres does not.
"""
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.models import Users

# A real user logging spending as it happens does not approach 50 parses in a day.
DAILY_LIMIT_STANDARD = 50
# Demo accounts are one tap from the landing page with no signup in front of them, so
# they get a tighter cap. Still far more than a judge needs to try the feature.
DAILY_LIMIT_DEMO = 15

# One statement, so there is no read-then-write race between two concurrent requests.
# CURRENT_DATE is the database's date, which keeps the reset boundary consistent
# regardless of which process serves the request.
_INCREMENT = text(
    """
    INSERT INTO ai_usage (user_id, usage_date, count)
    VALUES (:user_id, CURRENT_DATE, 1)
    ON CONFLICT (user_id, usage_date)
    DO UPDATE SET count = ai_usage.count + 1
    RETURNING count
    """
)


def daily_limit_for(user: Users) -> int:
    return DAILY_LIMIT_DEMO if user.is_demo else DAILY_LIMIT_STANDARD


def record_ai_call(db: Session, user: Users) -> tuple[int, int]:
    """
    Count one call against today's allowance and return (count_after, limit).

    The increment happens before the Anthropic call and is committed immediately, so a
    request that fails or times out still counts. That is intentional — a failed call
    can still have cost money, and it stops a caller from farming retries.

    Calls made while already over the limit keep incrementing. Harmless, and it leaves
    a record of how hard something was pushing.
    """
    count = db.execute(_INCREMENT, {"user_id": str(user.id)}).scalar_one()
    db.commit()
    return count, daily_limit_for(user)
