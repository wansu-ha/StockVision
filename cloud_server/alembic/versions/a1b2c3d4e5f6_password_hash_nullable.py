"""password_hash nullable

Revision ID: a1b2c3d4e5f6
Revises: 5fc19af729fc
Create Date: 2026-03-14 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '5fc19af729fc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 빈 문자열 password_hash → NULL 정리 (OAuth 전용 계정)
    op.execute("UPDATE users SET password_hash = NULL WHERE password_hash = ''")
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "password_hash",
            existing_type=sa.String(255),
            nullable=True,
        )


def downgrade() -> None:
    # NULL → 빈 문자열 복원 후 NOT NULL 복구
    op.execute("UPDATE users SET password_hash = '' WHERE password_hash IS NULL")
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "password_hash",
            existing_type=sa.String(255),
            nullable=False,
        )
