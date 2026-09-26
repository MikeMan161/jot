"""
Defines all SQLAlchemy ORM models in one place so relationships, foreign keys, and
cascade rules are easy to reason about together. These models are the single source
of truth for the database schema in Python. The SQL migration in
database/migrations/ should always match what is defined here.
"""
from sqlalchemy import Column, String, Numeric, Boolean, ForeignKey, text, DateTime, Date, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base

class Users(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    currency = Column(String, nullable=False, default="USD")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"), onupdate=text("now()"))
    monthly_income = Column(Numeric(10,2), server_default="0")
    # Marks a throwaway account created by POST /auth/demo. Demo rows are purged on
    # age, so created_at above is the cleanup key — there is no separate timestamp.
    is_demo = Column(Boolean, nullable=False, server_default=text("false"))

    buckets = relationship("Buckets", back_populates="user", cascade="all, delete")
    categories = relationship("Categories", back_populates="user", cascade="all, delete")
    transactions = relationship("Transactions", back_populates="user", cascade="all, delete")
    savings_goals = relationship("SavingsGoals", back_populates="user", cascade="all, delete")
    income = relationship("Income", back_populates="user", cascade="all, delete")
    debts = relationship("Debts", back_populates="user", cascade="all, delete")
    ai_usage = relationship("AiUsage", back_populates="user", cascade="all, delete")

class AiUsage(Base):
    """
    One row per user per day, counting calls to the paid AI endpoint. This lives in
    Postgres rather than in the in-process limiter because the per-minute burst limits
    only need to survive seconds, while the daily cost cap has to survive a redeploy —
    the process restarts, the Anthropic bill does not.
    """
    __tablename__ = "ai_usage"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    usage_date = Column(Date, primary_key=True)
    count = Column(Integer, nullable=False, server_default="0")

    user = relationship("Users", back_populates="ai_usage")

class UsageCounters(Base):
    """
    Counters that must outlive the rows they describe, keyed by an arbitrary scope
    string rather than by a user.

    This is separate from AiUsage on purpose. AiUsage.user_id cascade-deletes with the
    user, and demo accounts are purged every two hours, so a global total derived by
    summing AiUsage over demo users would reset as accounts cycle — which is the exact
    pattern a global cap has to catch. No foreign key here means no cascade.
    """
    __tablename__ = "usage_counters"

    scope = Column(String(64), primary_key=True)
    usage_date = Column(Date, primary_key=True)
    count = Column(Integer, nullable=False, server_default="0")

class Buckets(Base):
    __tablename__ = "buckets"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    bucket_type = Column(String, nullable=False)  
    target_percentage = Column(Numeric, nullable=False)
    alert_threshold = Column(Numeric, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"), onupdate=text("now()"))

    user = relationship("Users", back_populates="buckets")
    categories = relationship("Categories", back_populates="buckets")
    savings_goals = relationship("SavingsGoals", back_populates="buckets")

class Categories(Base):
    __tablename__ = "categories"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    bucket_id = Column(UUID(as_uuid=True), ForeignKey("buckets.id"), nullable=False)
    name = Column(String, nullable=False)
    is_default = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"), onupdate=text("now()"))

    user = relationship("Users", back_populates="categories")
    buckets = relationship("Buckets", back_populates="categories")
    transactions = relationship("Transactions", back_populates="category", cascade="all, delete")

class Transactions(Base):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"), nullable=True)
    amount = Column(Numeric, nullable=False)
    description = Column(String, nullable=True)
    merchant = Column(String, nullable=True)
    transaction_date = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"), onupdate=text("now()"))
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("Users", back_populates="transactions")
    category = relationship("Categories", back_populates="transactions")

class SavingsGoals(Base):
    __tablename__ = "savings_goals"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    bucket_id = Column(UUID(as_uuid=True), ForeignKey("buckets.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    target_amount = Column(Numeric, nullable=False)
    current_amount = Column(Numeric, nullable=False, default=0)
    due_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"), onupdate=text("now()"))
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("Users", back_populates="savings_goals")
    buckets = relationship("Buckets", back_populates="savings_goals")

class Income(Base):
    __tablename__ = "income"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Numeric, nullable=False)
    description = Column(String, nullable=True)
    source = Column(String, nullable=True)
    frequency = Column(String, nullable=False)
    income_date = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"), onupdate=text("now()"))
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("Users", back_populates="income")

class Debts(Base):
    __tablename__ = "debts"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    current_balance = Column(Numeric, nullable=False)
    apr = Column(Numeric, nullable=False)
    minimum_payment = Column(Numeric, nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"), onupdate=text("now()"))
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("Users", back_populates="debts")