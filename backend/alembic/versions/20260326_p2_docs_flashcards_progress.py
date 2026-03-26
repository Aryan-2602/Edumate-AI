"""P2: document indexing metadata, flashcards, nullable user_progress.document_id

Revision ID: p2_20260326
Revises:
Create Date: 2026-03-26

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "p2_20260326"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("chroma_collection_name", sa.String(), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("content_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("embedding_updated_at", sa.DateTime(), nullable=True),
    )

    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("user_progress") as batch_op:
            batch_op.alter_column(
                "document_id",
                existing_type=sa.Integer(),
                nullable=True,
            )
    else:
        op.alter_column(
            "user_progress",
            "document_id",
            existing_type=sa.Integer(),
            nullable=True,
        )

    op.create_table(
        "flashcard_sets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("source_document_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("card_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["source_document_id"],
            ["documents.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "flashcards",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("flashcard_set_id", sa.Integer(), nullable=False),
        sa.Column("front", sa.Text(), nullable=False),
        sa.Column("back", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["flashcard_set_id"],
            ["flashcard_sets.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("flashcards")
    op.drop_table("flashcard_sets")

    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("user_progress") as batch_op:
            batch_op.alter_column(
                "document_id",
                existing_type=sa.Integer(),
                nullable=False,
            )
    else:
        op.alter_column(
            "user_progress",
            "document_id",
            existing_type=sa.Integer(),
            nullable=False,
        )

    op.drop_column("documents", "embedding_updated_at")
    op.drop_column("documents", "content_hash")
    op.drop_column("documents", "chroma_collection_name")
