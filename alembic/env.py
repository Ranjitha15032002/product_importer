# alembic/env.py
import sys
import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

# allow importing app package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# this is the Alembic Config object, which provides access to the values within the .ini file.
config = context.config

# Interpret the config file for Python logging.
fileConfig(config.config_file_name)

# Import your models here for 'autogenerate' support
from app import models  # noqa: E402
target_metadata = models.Base.metadata

def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url, target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"}
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section), prefix="sqlalchemy.", poolclass=pool.NullPool
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
