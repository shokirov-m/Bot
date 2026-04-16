"""highest_floor_reached, class_tier, subclass_key для свободного перемещения и веток класса."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "8a9b3037bda5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("characters") as batch:
        batch.add_column(
            sa.Column(
                "highest_floor_reached",
                sa.Integer(),
                nullable=False,
                server_default="1",
            ),
        )
        batch.add_column(
            sa.Column(
                "class_tier",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
        )
        batch.add_column(
            sa.Column("subclass_key", sa.String(length=32), nullable=True),
        )
    op.execute(sa.text("UPDATE characters SET highest_floor_reached = floor_number"))
    # Уже существовавшие герои до обновления — с выбранным классом (не странник).
    op.execute(sa.text("UPDATE characters SET class_tier = 1 WHERE class_key != 'wanderer'"))


def downgrade() -> None:
    with op.batch_alter_table("characters") as batch:
        batch.drop_column("subclass_key")
        batch.drop_column("class_tier")
        batch.drop_column("highest_floor_reached")
