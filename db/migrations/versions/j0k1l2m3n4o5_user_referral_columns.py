"""Реферальные поля users: referred_by_user_id, referral_l2_payout_done."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "j0k1l2m3n4o5"
down_revision: Union[str, None] = "h3i4j5k6l7m8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("referred_by_user_id", sa.Integer(), nullable=True))
    op.add_column(
        "users",
        sa.Column("referral_l2_payout_done", sa.Boolean(), nullable=False, server_default="0"),
    )
    op.create_index("ix_users_referred_by_user_id", "users", ["referred_by_user_id"])


def downgrade() -> None:
    op.drop_index("ix_users_referred_by_user_id", table_name="users")
    op.drop_column("users", "referral_l2_payout_done")
    op.drop_column("users", "referred_by_user_id")
