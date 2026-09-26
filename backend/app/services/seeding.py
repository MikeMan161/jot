from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.models.models import Buckets, Categories, Debts, Income, SavingsGoals, Transactions

DEFAULT_BUCKETS = [
    ("Fixed Costs", "fixed_costs", 55, [
        "Rent/Mortgage", "Utilities", "Internet & Phone", "Groceries",
        "Transportation", "Insurance", "Debt Payments", "Subscriptions",
    ]),
    ("Investments", "investments", 10, [
        "401(k)", "Roth IRA", "Brokerage",
    ]),
    ("Savings", "savings", 10, [
        "Emergency Fund", "Vacation", "Big Purchases", "Gifts",
    ]),
    ("Guilt-Free Spending", "guilt_free", 25, [
        "Dining Out", "Entertainment", "Shopping", "Hobbies", "Travel", "Fitness",
    ]),
]
assert sum(pct for _, _, pct, _ in DEFAULT_BUCKETS) == 100
DEFAULT_ALERT_THRESHOLD = 80



def seed_default_buckets(db, user): 
    pairs = []
    for name, bucket_type, pct, category_names in DEFAULT_BUCKETS:
        bucket = Buckets(
            user_id=user.id,
            name=name,
            bucket_type=bucket_type,
            target_percentage=pct,
            alert_threshold=DEFAULT_ALERT_THRESHOLD
        )
        db.add(bucket)
        pairs.append((bucket,category_names))
    db.flush()
    for bucket, category_names in pairs:
        for category_name in category_names:
            db.add(Categories(user_id=user.id, bucket_id=bucket.id, name=category_name))


# --- Demo account sample data -------------------------------------------------------
#
# Income is fixed at $4,200/month, which makes the four targets $2,310 / $420 / $420 /
# $1,050. The amounts below are chosen against those targets so the dashboard tells a
# specific story the moment it opens:
#
#   Fixed Costs        ~77% of target   comfortable
#   Investments        ~71% of target   comfortable
#   Savings            ~65% of target   comfortable
#   Guilt-Free        ~85% of target   OVER the 80% alert threshold
#
# Exactly one bucket in alert. That demonstrates the alert without anyone having to
# trigger it, and it matches the product's point of view: the overspend is in the fun
# category, and the app flags it rather than scolding about it.

DEMO_MONTHLY_INCOME = Decimal("4200.00")

# (category name, amount, day of month, merchant, description)
_DEMO_THIS_MONTH = [
    # Fixed Costs — 1,782.37 of 2,310
    ("Rent/Mortgage",     "1050.00", 1,  "Sunrise Apartments",  "Rent"),
    ("Utilities",         "95.40",   3,  "City Power",          "Electric bill"),
    ("Internet & Phone",  "70.00",   5,  "Fios",                "Internet"),
    ("Groceries",         "82.15",   4,  "Publix",              "Weekly groceries"),
    ("Groceries",         "64.30",   11, "Publix",              "Weekly groceries"),
    ("Groceries",         "91.20",   18, "Trader Joe's",        "Weekly groceries"),
    ("Groceries",         "57.85",   24, "Publix",              "Weekly groceries"),
    ("Transportation",    "45.00",   7,  "Shell",               "Gas"),
    ("Transportation",    "38.50",   20, "Shell",               "Gas"),
    ("Subscriptions",     "15.99",   8,  "Netflix",             "Streaming"),
    ("Subscriptions",     "11.99",   12, "Spotify",             "Music"),
    ("Subscriptions",     "9.99",    15, "iCloud",              "Storage"),
    ("Debt Payments",     "150.00",  10, "Ally Auto",           "Car payment"),
    # Investments — 300.00 of 420
    ("401(k)",            "250.00",  1,  "Fidelity",            "Paycheck contribution"),
    ("Roth IRA",          "50.00",   15, "Fidelity",            "Monthly contribution"),
    # Savings — 275.00 of 420
    ("Emergency Fund",    "200.00",  2,  "Ally Bank",           "Automatic transfer"),
    ("Vacation",          "75.00",   16, "Ally Bank",           "Automatic transfer"),
    # Guilt-Free — 892.53 of 1,050 (85%, over the 80% threshold)
    ("Dining Out",        "68.40",   3,  "Bellwether",          "Dinner with friends"),
    ("Dining Out",        "42.15",   9,  "Maple Street Biscuit", "Brunch"),
    ("Dining Out",        "95.60",   14, "Ruth's Chris",        "Birthday dinner"),
    ("Dining Out",        "51.30",   21, "Hobos",               "Dinner"),
    ("Dining Out",        "73.85",   26, "Taverna",             "Dinner out"),
    ("Entertainment",     "54.99",   6,  "AMC Theatres",        "Movie night"),
    ("Entertainment",     "32.00",   17, "Ticketmaster",        "Comedy show"),
    ("Shopping",          "145.75",  8,  "Nordstrom",           "Jacket"),
    ("Shopping",          "89.99",   19, "Nike",                "Running shoes"),
    ("Hobbies",           "62.50",   13, "Guitar Center",       "Strings and picks"),
    ("Travel",            "118.00",  22, "Delta",               "Flight to Atlanta"),
    ("Fitness",           "58.00",   5,  "Anytime Fitness",     "Gym membership"),
]

# A short tail of last month so the transactions list and charts have history. These
# fall outside the current-month window get_bucket_spending uses, so they deliberately
# do not affect the bucket percentages above.
_DEMO_LAST_MONTH = [
    ("Rent/Mortgage",  "1050.00", 4,  "Sunrise Apartments", "Rent"),
    ("Groceries",      "88.40",   9,  "Publix",             "Weekly groceries"),
    ("Dining Out",     "61.25",   14, "Bellwether",         "Dinner"),
    ("Shopping",       "39.99",   19, "Target",             "Household"),
    ("Transportation", "41.75",   24, "Shell",              "Gas"),
]


def seed_demo_data(db, user):
    """
    Fills a freshly created demo account with a month of believable activity.

    Call after seed_default_buckets and after a flush, because every transaction needs
    a category_id and every goal needs a bucket_id.

    Dates are relative to today so the data never looks stale. Day-of-month values are
    clamped to today, which means a demo created on the 2nd bunches the month's
    transactions into the first two days rather than dropping them. That keeps the
    bucket percentages — and so the alert on Guilt-Free — identical no matter when
    someone clicks the demo button.
    """
    now = datetime.now(timezone.utc)
    # Noon rather than midnight so a timezone shift on the client cannot push a
    # transaction into the previous day and out of the month window.
    month_start = now.replace(day=1, hour=12, minute=0, second=0, microsecond=0)
    last_month_end = month_start - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)

    categories = {
        category.name: category.id
        for category in db.query(Categories).filter(Categories.user_id == user.id).all()
    }
    buckets = {
        bucket.bucket_type: bucket.id
        for bucket in db.query(Buckets).filter(Buckets.user_id == user.id).all()
    }

    def add_rows(rows, anchor, max_day):
        for name, amount, day, merchant, description in rows:
            db.add(Transactions(
                user_id=user.id,
                category_id=categories[name],
                amount=Decimal(amount),
                description=description,
                merchant=merchant,
                transaction_date=anchor.replace(day=min(day, max_day)),
            ))

    add_rows(_DEMO_THIS_MONTH, month_start, now.day)
    add_rows(_DEMO_LAST_MONTH, last_month_start, last_month_end.day)

    db.add(Income(
        user_id=user.id,
        amount=DEMO_MONTHLY_INCOME,
        description="Monthly paycheck",
        source="Northline Logistics",
        frequency="monthly",
        income_date=month_start,
    ))

    db.add(SavingsGoals(
        user_id=user.id,
        bucket_id=buckets["savings"],
        name="Emergency fund",
        description="Three months of expenses",
        target_amount=Decimal("6000.00"),
        current_amount=Decimal("2400.00"),
        due_date=now + timedelta(days=240),
    ))
    db.add(SavingsGoals(
        user_id=user.id,
        bucket_id=buckets["savings"],
        name="Japan trip",
        description="Flights and two weeks of travel",
        target_amount=Decimal("3500.00"),
        current_amount=Decimal("1150.00"),
        due_date=now + timedelta(days=300),
    ))

    db.add(Debts(
        user_id=user.id,
        name="Car loan",
        current_balance=Decimal("8400.00"),
        apr=Decimal("5.90"),
        minimum_payment=Decimal("150.00"),
        due_date=now + timedelta(days=14),
    ))

