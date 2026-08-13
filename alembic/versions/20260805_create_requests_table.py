"""Create requests domain tables

Revision ID: 20260805_create_requests
Revises: 20260804_create_users
Create Date: 2026-08-05 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "20260805_create_requests"
down_revision = "20260804_create_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "environments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("variables", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name", name="uq_environments_user_id_name"),
    )
    op.create_index(op.f("ix_environments_id"), "environments", ["id"], unique=False)
    op.create_index(op.f("ix_environments_user_id"), "environments", ["user_id"], unique=False)

    op.create_table(
        "collections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("is_favorite", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name", name="uq_collections_user_id_name"),
    )
    op.create_index(op.f("ix_collections_id"), "collections", ["id"], unique=False)
    op.create_index(op.f("ix_collections_user_id"), "collections", ["user_id"], unique=False)

    op.create_table(
        "collection_tags",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("collection_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(["collection_id"], ["collections.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("collection_id", "name", name="uq_collection_tags_collection_id_name"),
    )
    op.create_index(op.f("ix_collection_tags_id"), "collection_tags", ["id"], unique=False)
    op.create_index(op.f("ix_collection_tags_collection_id"), "collection_tags", ["collection_id"], unique=False)

    op.create_table(
        "requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("collection_id", sa.Uuid(), nullable=True),
        sa.Column("environment_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("method", sa.String(length=10), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("body_type", sa.String(length=20), nullable=False),
        sa.Column("timeout", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("follow_redirects", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("verify_ssl", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_favorite", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["environment_id"], ["environments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_requests_id"), "requests", ["id"], unique=False)
    op.create_index(op.f("ix_requests_user_id"), "requests", ["user_id"], unique=False)
    op.create_index(op.f("ix_requests_collection_id"), "requests", ["collection_id"], unique=False)
    op.create_index(op.f("ix_requests_environment_id"), "requests", ["environment_id"], unique=False)

    op.create_table(
        "request_headers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("value", sa.String(length=2048), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.ForeignKeyConstraint(["request_id"], ["requests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id", "key", name="uq_request_headers_request_id_key"),
    )
    op.create_index(op.f("ix_request_headers_id"), "request_headers", ["id"], unique=False)
    op.create_index(op.f("ix_request_headers_request_id"), "request_headers", ["request_id"], unique=False)

    op.create_table(
        "request_query_parameters",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("value", sa.String(length=2048), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.ForeignKeyConstraint(["request_id"], ["requests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id", "key", name="uq_request_query_parameters_request_id_key"),
    )
    op.create_index(op.f("ix_request_query_parameters_id"), "request_query_parameters", ["id"], unique=False)
    op.create_index(op.f("ix_request_query_parameters_request_id"), "request_query_parameters", ["request_id"], unique=False)

    op.create_table(
        "request_authorizations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("token", sa.String(length=4096), nullable=True),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("password", sa.String(length=255), nullable=True),
        sa.Column("api_key_name", sa.String(length=255), nullable=True),
        sa.Column("api_key_value", sa.String(length=4096), nullable=True),
        sa.Column("api_key_in", sa.String(length=20), nullable=True),
        sa.ForeignKeyConstraint(["request_id"], ["requests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id", name="uq_request_authorizations_request_id"),
    )
    op.create_index(op.f("ix_request_authorizations_id"), "request_authorizations", ["id"], unique=False)
    op.create_index(op.f("ix_request_authorizations_request_id"), "request_authorizations", ["request_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_request_authorizations_request_id"), table_name="request_authorizations")
    op.drop_index(op.f("ix_request_authorizations_id"), table_name="request_authorizations")
    op.drop_table("request_authorizations")

    op.drop_index(op.f("ix_collection_tags_collection_id"), table_name="collection_tags")
    op.drop_index(op.f("ix_collection_tags_id"), table_name="collection_tags")
    op.drop_table("collection_tags")

    op.drop_index(op.f("ix_collections_user_id"), table_name="collections")
    op.drop_index(op.f("ix_collections_id"), table_name="collections")
    op.drop_table("collections")

    op.drop_index(op.f("ix_request_query_parameters_request_id"), table_name="request_query_parameters")
    op.drop_index(op.f("ix_request_query_parameters_id"), table_name="request_query_parameters")
    op.drop_table("request_query_parameters")

    op.drop_index(op.f("ix_request_headers_request_id"), table_name="request_headers")
    op.drop_index(op.f("ix_request_headers_id"), table_name="request_headers")
    op.drop_table("request_headers")

    op.drop_index(op.f("ix_requests_environment_id"), table_name="requests")
    op.drop_index(op.f("ix_requests_collection_id"), table_name="requests")
    op.drop_index(op.f("ix_requests_user_id"), table_name="requests")
    op.drop_index(op.f("ix_requests_id"), table_name="requests")
    op.drop_table("requests")

    op.drop_index(op.f("ix_environments_user_id"), table_name="environments")
    op.drop_index(op.f("ix_environments_id"), table_name="environments")
    op.drop_table("environments")
