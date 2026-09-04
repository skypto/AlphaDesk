"""Version invitation codes for strict server-side registration.

Revision ID: 20260902_0008
Revises: 20260902_0007
Create Date: 2026-09-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260902_0008"
down_revision: str | None = "20260902_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "invitations",
        sa.Column(
            "code_format",
            sa.String(length=32),
            nullable=False,
            server_default="legacy_urlsafe",
        ),
    )


def downgrade() -> None:
    op.drop_column("invitations", "code_format")
