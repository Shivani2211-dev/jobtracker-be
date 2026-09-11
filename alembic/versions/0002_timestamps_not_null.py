"""make created_at / updated_at NOT NULL, matching the models

Revision ID: 0002_timestamps_not_null
Revises: 0001_initial
Create Date: 2026-09-11
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_timestamps_not_null"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

# The models always declared these columns NOT NULL, but 0001 created them
# nullable. Nothing noticed because the app built its own tables with
# create_all() instead of running migrations; `alembic check` in CI now
# catches this kind of drift.
TIMESTAMPS = {
    "users": ["created_at"],
    "jobs": ["created_at", "updated_at"],
    "applications": ["created_at", "updated_at"],
}


def upgrade() -> None:
    # Databases first built by create_all() also picked up ix_<table>_id
    # indexes from the old models. No migration ever created them, and a
    # primary key is already indexed, so drop them wherever they exist and let
    # every environment converge on the same schema.
    inspector = sa.inspect(op.get_bind())
    for table in TIMESTAMPS:
        legacy = f"ix_{table}_id"
        if legacy in {index["name"] for index in inspector.get_indexes(table)}:
            op.drop_index(legacy, table_name=table)

    for table, columns in TIMESTAMPS.items():
        # SET NOT NULL fails if any row is still NULL, so backfill first.
        for column in columns:
            op.execute(f"UPDATE {table} SET {column} = CURRENT_TIMESTAMP WHERE {column} IS NULL")
        # batch_alter_table lets SQLite, which can't alter a column in place,
        # apply the same change Postgres does with ALTER COLUMN.
        with op.batch_alter_table(table) as batch:
            for column in columns:
                batch.alter_column(column, existing_type=sa.DateTime(timezone=True), nullable=False)


def downgrade() -> None:
    for table, columns in TIMESTAMPS.items():
        with op.batch_alter_table(table) as batch:
            for column in columns:
                batch.alter_column(column, existing_type=sa.DateTime(timezone=True), nullable=True)
