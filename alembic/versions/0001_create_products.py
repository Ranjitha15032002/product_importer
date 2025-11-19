# alembic/versions/0001_create_products.py
"""create products table with generated sku_lower

Revision ID: 0001_create_products
Revises:
Create Date: 2025-11-19 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '0001_create_products'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.execute("""
    CREATE TABLE products (
      id serial PRIMARY KEY,
      sku text NOT NULL,
      sku_lower text GENERATED ALWAYS AS (lower(sku)) STORED NOT NULL,
      name text NOT NULL,
      description text,
      price_cents integer,
      active boolean NOT NULL DEFAULT true,
      created_at timestamptz NOT NULL DEFAULT now(),
      updated_at timestamptz NOT NULL DEFAULT now()
    );
    """)
    op.create_index('uq_products_sku_lower', 'products', ['sku_lower'], unique=True)

def downgrade():
    op.drop_index('uq_products_sku_lower', table_name='products')
    op.execute("DROP TABLE products;")
