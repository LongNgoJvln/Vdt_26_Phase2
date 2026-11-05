"""Add owner-scoped network snapshot and change-proposal records.

Revision ID: 0006_network_change_records
Revises: 0005_user_settings
Create Date: 2026-09-11
"""
from alembic import op
import sqlalchemy as sa


revision = "0006_network_change_records"
down_revision = "0005_user_settings"
branch_labels = None
depends_on = None


def _table_exists(bind, name: str) -> bool:
    return name in sa.inspect(bind).get_table_names()


def upgrade() -> None:
    bind = op.get_bind()

    if not _table_exists(bind, "network_snapshots"):
        op.create_table(
            "network_snapshots",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("owner", sa.String(), nullable=True),
            sa.Column("cluster", sa.String(), nullable=True),
            sa.Column("namespace", sa.String(), nullable=True),
            sa.Column("target_json", sa.Text(), nullable=False),
            sa.Column("observations_json", sa.Text(), nullable=False),
            sa.Column("warnings_json", sa.Text(), nullable=False),
            sa.Column("captured_at", sa.DateTime(), nullable=False),
            sa.Column("content_hash", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_network_snapshots_id", "network_snapshots", ["id"])
        op.create_index("ix_network_snapshots_owner", "network_snapshots", ["owner"])
        op.create_index("ix_network_snapshots_cluster", "network_snapshots", ["cluster"])
        op.create_index("ix_network_snapshots_namespace", "network_snapshots", ["namespace"])
        op.create_index("ix_network_snapshots_captured_at", "network_snapshots", ["captured_at"])
        op.create_index("ix_network_snapshots_content_hash", "network_snapshots", ["content_hash"])
        op.create_index("ix_network_snapshots_owner_captured", "network_snapshots", ["owner", "captured_at"])

    if not _table_exists(bind, "network_change_proposals"):
        op.create_table(
            "network_change_proposals",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("owner", sa.String(), nullable=True),
            sa.Column("session_id", sa.String(), nullable=True),
            sa.Column("snapshot_id", sa.String(), nullable=True),
            sa.Column("objective", sa.Text(), nullable=False),
            sa.Column("target_json", sa.Text(), nullable=False),
            sa.Column("plan_json", sa.Text(), nullable=False),
            sa.Column("artifact_json", sa.Text(), nullable=False),
            sa.Column("validation_json", sa.Text(), nullable=False),
            sa.Column("evidence_json", sa.Text(), nullable=False),
            sa.Column("risk", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["snapshot_id"], ["network_snapshots.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_network_change_proposals_id", "network_change_proposals", ["id"])
        op.create_index("ix_network_change_proposals_owner", "network_change_proposals", ["owner"])
        op.create_index("ix_network_change_proposals_session_id", "network_change_proposals", ["session_id"])
        op.create_index("ix_network_change_proposals_snapshot_id", "network_change_proposals", ["snapshot_id"])
        op.create_index("ix_network_change_proposals_risk", "network_change_proposals", ["risk"])
        op.create_index("ix_network_change_proposals_status", "network_change_proposals", ["status"])
        op.create_index("ix_network_change_proposals_owner_created", "network_change_proposals", ["owner", "created_at"])
        op.create_index("ix_network_change_proposals_owner_status", "network_change_proposals", ["owner", "status"])


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS network_change_proposals")
    op.execute("DROP TABLE IF EXISTS network_snapshots")
