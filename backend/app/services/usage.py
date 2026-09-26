"""
Daily quotas for the paid AI endpoint.

These are the caps that actually bound the Anthropic bill. The in-memory burst limiter
in app/limiter.py stops someone hammering the endpoint for a minute, but its counters
die with the process, so a redeploy hands everyone a fresh allowance. Rows in Postgres
do not.

Two caps, because a per-user cap alone does not bound spending when accounts are free
to create:

  - Per user, per day. Keyed on the user, so one person's usage cannot exhaust
    everyone else's.
  - Global, per day, across all demo accounts. A demo account is one tap from the
    landing page, so a per-user cap on its own only limits what one *account* can
    spend — and an attacker who can create accounts just creates more. At 30 demo
    creations an hour from a single IP, a per-user-only cap would allow hundreds of
    accounts a day each carrying a fresh allowance. The global counter is what turns
    that into a fixed ceiling.

The global counter deliberately does not live in ai_usage. That table's user_id
cascade-deletes with the user, and demo accounts are purged every two hours, so a
total summed from it would reset as accounts cycle — precisely the abuse it is meant
to catch. usage_counters has no foreign key for that reason.
"""
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.models import Users

# A real user logging spending as it happens does not approach 50 parses in a day.
DAILY_LIMIT_STANDARD = 50
# Demo accounts are one tap from the landing page with no signup in front of them, so
# they get a tighter cap. Still far more than a judge needs to try the feature.
DAILY_LIMIT_DEMO = 15

# Ceiling on everything every demo account spends in a day, combined. Sized to absorb
# a launch-day spike or a room of judges — a few hundred parses is well beyond
# realistic demo traffic — while capping what abuse can cost regardless of how many
# accounts get created.
GLOBAL_DEMO_DAILY_LIMIT = 500
GLOBAL_DEMO_SCOPE = "demo_ai"

# Single statements, so there is no read-then-write race between concurrent requests.
# CURRENT_DATE is the database's date, which keeps the reset boundary consistent
# regardless of which process serves the request.
_INCREMENT_USER = text(
    """
    INSERT INTO ai_usage (user_id, usage_date, count)
    VALUES (:user_id, CURRENT_DATE, 1)
    ON CONFLICT (user_id, usage_date)
    DO UPDATE SET count = ai_usage.count + 1
    RETURNING count
    """
)

_INCREMENT_SCOPE = text(
    """
    INSERT INTO usage_counters (scope, usage_date, count)
    VALUES (:scope, CURRENT_DATE, 1)
    ON CONFLICT (scope, usage_date)
    DO UPDATE SET count = usage_counters.count + 1
    RETURNING count
    """
)


@dataclass(frozen=True)
class QuotaStatus:
    """
    Outcome of counting one call. `exceeded` names which cap was hit so the caller can
    say something accurate — "you have used yours up" and "the shared demo allowance is
    gone" need different messages and suggest different next steps.
    """
    allowed: bool
    exceeded: str | None = None  # None, "user", or "global"


def daily_limit_for(user: Users) -> int:
    return DAILY_LIMIT_DEMO if user.is_demo else DAILY_LIMIT_STANDARD


def record_ai_call(db: Session, user: Users) -> QuotaStatus:
    """
    Count one call against today's allowances and report whether it may proceed.

    The increment happens before the Anthropic call and is committed immediately, so a
    request that fails or times out still counts. That is intentional — a failed call
    can still have cost money, and it stops a caller from farming retries.

    Calls made while already over a limit keep incrementing. Harmless, and it leaves a
    record of how hard something was pushing.
    """
    user_count = db.execute(_INCREMENT_USER, {"user_id": str(user.id)}).scalar_one()

    global_count = None
    if user.is_demo:
        global_count = db.execute(
            _INCREMENT_SCOPE, {"scope": GLOBAL_DEMO_SCOPE}
        ).scalar_one()

    db.commit()

    # Personal limit first: it is the one the user caused and the one they can do
    # something about, so it is the more useful thing to be told.
    if user_count > daily_limit_for(user):
        return QuotaStatus(allowed=False, exceeded="user")
    if global_count is not None and global_count > GLOBAL_DEMO_DAILY_LIMIT:
        return QuotaStatus(allowed=False, exceeded="global")
    return QuotaStatus(allowed=True)
