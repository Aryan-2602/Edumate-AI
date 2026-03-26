"""Document processing_status and processing_error for async ingestion.

Revision ID: doc_proc_20260327
Revises: p2_20260326
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision: str = "doc_proc_20260327"
down_revision: Union[str, None] = "p2_20260326"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("processing_status", sa.String(), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("processing_error", sa.Text(), nullable=True),
    )
    op.execute(
        text(
            "UPDATE documents SET processing_status = 'completed' "
            "WHERE is_processed = 1"
        )
    )
    op.execute(
        text(
            "UPDATE documents SET processing_status = 'pending' "
            "WHERE processing_status IS NULL"
        )
    )
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("documents") as batch_op:
            batch_op.alter_column(
                "processing_status",
                existing_type=sa.String(),
                nullable=False,
                server_default=sa.text("'pending'"),
            )
    else:
        op.alter_column(
            "documents",
            "processing_status",
            existing_type=sa.String(),
            nullable=False,
            server_default="pending",
        )


def downgrade() -> None:
    op.drop_column("documents", "processing_error")
    op.drop_column("documents", "processing_status")
