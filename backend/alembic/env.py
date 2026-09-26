"""
Alembic environment. Four things differ from the generated scaffold:

1. The backend directory is put on sys.path so `app.*` imports resolve no matter which
   directory alembic is invoked from.
2. The database URL comes from the DATABASE_URL environment variable, not from
   alembic.ini. alembic.ini is committed, so a URL there would put the RDS password in
   git. This mirrors how app/database.py reads the same variable.
3. target_metadata points at the app's own Base, and app.models.models is imported for
   its side effects — importing the module is what registers all seven tables on
   Base.metadata. Without that import the metadata is empty.
4. compare_type is left OFF. The models and the original hand-written DDL have drifted
   (models say String where the DDL says VARCHAR(255)), so --autogenerate would emit
   spurious column-type rewrites against live data. Revisions are hand-written until
   that drift is reconciled.
"""
import os
import sys
from pathlib import Path
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from dotenv import load_dotenv

from alembic import context

# env.py sits at backend/alembic/env.py, so parent.parent is backend/ — the same
# relative depth app/database.py and app/auth.py use to find the .env file.
BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR / ".env")

from app.database import Base
from app.models import models  # noqa: F401 — imported so the tables register on Base.metadata

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

database_url = os.getenv("DATABASE_URL")
if not database_url:
    # Fail loudly rather than falling back to a default, matching how the app itself
    # refuses to start on a missing secret.
    raise RuntimeError(
        "DATABASE_URL is not set. Alembic reads it from the environment (or backend/.env) "
        "so the connection string is never committed in alembic.ini."
    )
config.set_main_option("sqlalchemy.url", database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
