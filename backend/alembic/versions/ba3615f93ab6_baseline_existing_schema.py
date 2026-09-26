"""baseline existing schema

Deliberately empty. Jot's seven tables were created before Alembic was adopted, so
there is no revision that builds them. This is a marker: applying it with
`alembic stamp head` tells Alembic that everything up to this point already exists,
so `upgrade` starts from the next revision instead of trying to create tables that
are already there.

Consequence worth knowing: a brand-new empty database cannot be built by running
`alembic upgrade head` from scratch — it would skip straight past the seven tables.
Bootstrapping a fresh database still needs database/migrations/001_create_tables.sql
until this baseline is backfilled with the real CREATE TABLE statements.

Revision ID: ba3615f93ab6
Revises:
Create Date: 2026-09-26 13:28:54.108435

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ba3615f93ab6'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
