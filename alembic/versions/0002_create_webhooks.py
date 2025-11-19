# alembic/versions/0002_create_webhooks.py
"""create webhooks table

Revision ID: 0002_create_webhooks
Revises: 0001_create_products
Create Date: 2025-11-19 00:05:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '0002_create_webhooks'
down_revision = '0001_create_products'
branch_labels = None
depends_on = None

def upgrade():
    op.execute("""
    CREATE TABLE webhooks (
      id serial PRIMARY KEY,
      name text,
      url text NOT NULL,
      event text NOT NULL,
      enabled boolean NOT NULL DEFAULT true,
      last_status text,
      last_response_time_ms integer,
      created_at timestamptz NOT NULL DEFAULT now(),
      updated_at timestamptz NOT NULL DEFAULT now()
    );
    """)

def downgrade():
    op.execute("DROP TABLE webhooks;")
