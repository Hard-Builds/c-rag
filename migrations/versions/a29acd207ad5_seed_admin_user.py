"""seed admin user

Revision ID: a29acd207ad5
Revises: c9c134865f58
Create Date: 2026-06-18 12:24:13.842765

"""
from typing import Sequence, Union

import uuid6
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a29acd207ad5'
down_revision: Union[str, None] = 'c9c134865f58'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ADMIN_EMAIL = "hardik@gmail.com"


def upgrade() -> None:
    op.execute(
        sa.text(
            f"INSERT INTO users (id, email, role) "
            f"VALUES ('{uuid6.uuid7()}'::uuid, '{ADMIN_EMAIL}', 'admin') "
            f"ON CONFLICT (email) DO NOTHING"
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM users WHERE email = :email").bindparams(email=ADMIN_EMAIL)
    )
