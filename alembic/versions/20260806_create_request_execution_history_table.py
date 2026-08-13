"""Create request execution history table

Revision ID: 20260806_create_request_execution_history
Revises: 20260805_create_requests
Create Date: 2026-08-06 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "20260806_create_req_history"
down_revision = "20260805_create_requests"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "request_execution_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("request_snapshot", sa.Text(), nullable=False),
        sa.Column("response_snapshot", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Float(), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("execution_status", sa.String(length=30), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("error", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["request_id"], ["requests.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_request_execution_history_id"), "request_execution_history", ["id"], unique=False)
    op.create_index(op.f("ix_request_execution_history_request_id"), "request_execution_history", ["request_id"], unique=False)
    op.create_index(op.f("ix_request_execution_history_user_id"), "request_execution_history", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_request_execution_history_user_id"), table_name="request_execution_history")
    op.drop_index(op.f("ix_request_execution_history_request_id"), table_name="request_execution_history")
    op.drop_index(op.f("ix_request_execution_history_id"), table_name="request_execution_history")
    op.drop_table("request_execution_history")
