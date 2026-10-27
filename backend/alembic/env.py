"""
Alembic Environment Configuration — AICTE FlowOps

Reads the real DATABASE_URL from ``app.config`` so migrations always
target the correct database without hard-coding the URL in ``alembic.ini``.
"""

import sys
from pathlib import Path
from logging.config import fileConfig

# Add backend directory to sys.path so app modules are resolvable
backend_dir = str(Path(__file__).resolve().parent.parent)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from sqlalchemy import engine_from_config, pool

from alembic import context

# Alembic Config object (gives access to .ini values)
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── Import all models so Alembic can detect them ────────────────────────
from app.database import Base  # noqa: E402
# Future model imports go here so autogenerate picks them up:
# from app.models import user, application, ...

target_metadata = Base.metadata

# ── Override sqlalchemy.url from application config ─────────────────────
from app.config import get_settings  # noqa: E402

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — emits SQL to stdout."""
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
    """Run migrations in 'online' mode — connects to the DB."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
