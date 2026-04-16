"""Публичный game_id у персонажей (арена, отображение)."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "k0a1b2c3d4e5"
down_revision: Union[str, None] = "j0k1l2m3n4o5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("characters", sa.Column("game_id", sa.Integer(), nullable=True))
    op.create_index("ix_characters_game_id", "characters", ["game_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_characters_game_id", table_name="characters")
    op.drop_column("characters", "game_id")
