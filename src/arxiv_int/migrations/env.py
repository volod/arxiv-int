"""Alembic environment for the owned canonical schemas.

The comparison target is contract-derived metadata restricted to owned schemas and
tables. dbt relations, extension internals, and other applications are excluded.
"""

from alembic import context
from sqlalchemy import engine_from_config, pool

from arxiv_int.contracts.migrations.runner import owned_object_filter, target_metadata

config = context.config
metadata = target_metadata()


def run_migrations_offline() -> None:
    """Emit SQL for review without connecting to a database."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=metadata,
        literal_binds=True,
        include_schemas=True,
        include_object=owned_object_filter(metadata),
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Apply revisions against an explicitly selected database."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=metadata,
            include_schemas=True,
            include_object=owned_object_filter(metadata),
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
