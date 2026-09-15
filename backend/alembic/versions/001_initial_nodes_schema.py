"""initial nodes schema

Revision ID: 001_initial_nodes
Revises: 
Create Date: 2026-09-15 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "001_initial_nodes"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "nodes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("node_id", sa.String(length=64), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("owner_id", sa.String(length=64), nullable=True),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("sdk_version", sa.String(length=32), nullable=False),
        sa.Column("device_name", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("health_status", sa.String(length=32), nullable=False),
        sa.Column("capabilities", JSONB().with_variant(sa.JSON(), "sqlite"), nullable=False),
        sa.Column("observed_public_ip", sa.String(length=64), nullable=True),
        sa.Column("download_mbps", sa.Float(), nullable=True),
        sa.Column("upload_mbps", sa.Float(), nullable=True),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_nodes_id"), "nodes", ["id"], unique=False)
    op.create_index(op.f("ix_nodes_node_id"), "nodes", ["node_id"], unique=True)
    op.create_index(op.f("ix_nodes_token_hash"), "nodes", ["token_hash"], unique=False)
    op.create_index(op.f("ix_nodes_owner_id"), "nodes", ["owner_id"], unique=False)
    op.create_index(op.f("ix_nodes_status"), "nodes", ["status"], unique=False)
    op.create_index(op.f("ix_nodes_health_status"), "nodes", ["health_status"], unique=False)
    op.create_index(op.f("ix_nodes_last_heartbeat_at"), "nodes", ["last_heartbeat_at"], unique=False)
    op.create_index("ix_nodes_status_last_heartbeat", "nodes", ["status", "last_heartbeat_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_nodes_status_last_heartbeat", table_name="nodes")
    op.drop_index(op.f("ix_nodes_last_heartbeat_at"), table_name="nodes")
    op.drop_index(op.f("ix_nodes_health_status"), table_name="nodes")
    op.drop_index(op.f("ix_nodes_status"), table_name="nodes")
    op.drop_index(op.f("ix_nodes_owner_id"), table_name="nodes")
    op.drop_index(op.f("ix_nodes_token_hash"), table_name="nodes")
    op.drop_index(op.f("ix_nodes_node_id"), table_name="nodes")
    op.drop_index(op.f("ix_nodes_id"), table_name="nodes")
    op.drop_table("nodes")
