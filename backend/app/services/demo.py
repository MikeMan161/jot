"""
Throwaway demo accounts.

Every visitor who taps "Try the demo" gets their own account rather than sharing one.
A single shared login would mean three judges on Proof Night mutating the same rows at
once, watching each other's transactions appear, and any one of them able to wreck the
data right before the next person looks at it.

The accounts are real rows in the users table, distinguished only by is_demo. That
means every existing route, ownership check, and cascade rule applies to them with no
special-casing — a demo user is a user that gets deleted later.
"""
import logging
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.auth import hash_password
from app.models.models import Users
from app.services.seeding import DEMO_MONTHLY_INCOME, seed_default_buckets, seed_demo_data

logger = logging.getLogger(__name__)

# Long enough that a judge can wander off mid-demo and come back to their data, short
# enough that the table does not accumulate. Cleanup runs on demo creation rather than
# on a schedule, so there is no cron or worker process to maintain on Elastic Beanstalk.
DEMO_LIFETIME = timedelta(hours=2)

# Not a real domain. Demo addresses must never collide with an address a person could
# actually register or receive mail at.
DEMO_EMAIL_DOMAIN = "demo.spendwithjot.com"


def purge_expired_demo_users(db: Session) -> int:
    """
    Delete demo accounts older than DEMO_LIFETIME and return how many went.

    Deletes through the ORM rather than with a bulk DELETE so SQLAlchemy orders the
    child deletes correctly. savings_goals references buckets with no ON DELETE rule,
    so a bulk delete of users relies on Postgres resolving both cascades within one
    statement; letting the ORM walk the relationships removes that assumption.
    """
    cutoff = datetime.now(timezone.utc) - DEMO_LIFETIME
    expired = db.query(Users).filter(
        Users.is_demo.is_(True),
        Users.created_at < cutoff,
    ).all()

    for user in expired:
        db.delete(user)

    if expired:
        logger.info("Purged %d expired demo user(s)", len(expired))
    return len(expired)


def create_demo_user(db: Session) -> Users:
    """
    Create one demo account, seeded with the four buckets and a month of sample data.

    Does not commit — the caller owns the transaction, matching how register() wraps
    user creation and bucket seeding in a single unit of work.
    """
    suffix = secrets.token_hex(8)

    user = Users(
        username=f"demo-{suffix}",
        email=f"demo-{suffix}@{DEMO_EMAIL_DOMAIN}",
        # The account needs a password hash (the column is NOT NULL) but must not be
        # reachable by password. Hashing a fresh random secret that is never stored
        # anywhere means there is no password that opens this account — the only way
        # in is the token handed back by the endpoint that created it.
        password_hash=hash_password(secrets.token_urlsafe(32)),
        currency="USD",
        monthly_income=DEMO_MONTHLY_INCOME,
        is_demo=True,
    )
    db.add(user)
    db.flush()

    seed_default_buckets(db, user)
    db.flush()
    seed_demo_data(db, user)

    return user
