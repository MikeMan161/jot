"""add usage_counters for global quotas

A deliberately FK-free counter table, keyed by an arbitrary scope string.

It exists separately from ai_usage because ai_usage.user_id cascade-deletes with
the user. Demo accounts are purged every two hours, so any total derived by summing
ai_usage over demo users resets as accounts cycle — which is exactly the pattern a
global cap needs to catch. A counter with no foreign key survives the purge.

Revision ID: b6ae34b1997a
Revises: 1aec1c0c0ba4
Create Date: 2026-09-26 18:14:02.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b6ae34b1997a'
down_revision: Union[str, Sequence[str], None] = '1aec1c0c0ba4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "usage_counters",
        sa.Column("scope", sa.String(length=64), primary_key=True),
        sa.Column("usage_date", sa.Date(), primary_key=True),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("usage_counters")
