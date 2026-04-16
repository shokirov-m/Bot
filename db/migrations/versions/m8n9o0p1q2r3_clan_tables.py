"""Таблицы clans и clan_memberships."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "m8n9o0p1q2r3"
down_revision: Union[str, None] = "k0a1b2c3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "clans",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("leader_character_id", sa.Integer(), nullable=False),
        sa.Column("chat_url", sa.String(length=256), nullable=True),
        sa.Column("clan_xp", sa.Integer(), server_default="0", nullable=False),
        sa.Column("clan_level", sa.Integer(), server_default="1", nullable=False),
        sa.ForeignKeyConstraint(
            ["leader_character_id"],
            ["characters.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "clan_memberships",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("clan_id", sa.Integer(), nullable=False),
        sa.Column("character_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=16), server_default="member", nullable=False),
        sa.ForeignKeyConstraint(["clan_id"], ["clans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("character_id"),
    )
    op.create_index("ix_clan_memberships_clan_id", "clan_memberships", ["clan_id"])


def downgrade() -> None:
    op.drop_index("ix_clan_memberships_clan_id", table_name="clan_memberships")
    op.drop_table("clan_memberships")
    op.drop_table("clans")
