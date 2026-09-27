"""add customer_persona to ai_quality_eval_type enum

Revision ID: f2a7c9e4b1d3
Revises: c16f41edc4fb
Create Date: 2026-09-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'f2a7c9e4b1d3'
down_revision: Union[str, None] = 'c16f41edc4fb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE ai_quality_eval_type ADD VALUE IF NOT EXISTS 'customer_persona'")


def downgrade() -> None:
    # Postgres does not support removing enum values; the label is left in place
    # (harmless — nothing writes it once the app code is rolled back).
    pass
