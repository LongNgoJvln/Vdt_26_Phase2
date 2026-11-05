"""Add scheduled-email / message-cache tables.

Revision ID: 0002_email_tables
Revises: 0001_initial_schema
Create Date: 2026-08-18

These 9 tables back the email scheduling + AI cache surface that
previously lived in the shadow ``data/scheduled_emails.db`` SQLite
file. They are added by the models (and therefore covered by
``Base.metadata.create_all`` in 0001 on fresh installs), but
deployments that already ran 0001 before these models existed need an
explicit migration so ``alembic upgrade head`` produces them.

Composite primary keys:

* ``email_tags (message_id, owner)`` — Message-IDs are global (a
  newsletter delivered to many users shares the same Message-ID);
  owner-scoping prevents one tenant clobbering another's tag row and
  leaking UIDs through IMAP filters.
* ``email_event_seen (owner, account_key, folder, message_key)`` —
  cross-tenant scans can't share a seen-row by construction.
"""
from alembic import op
import sqlalchemy as sa


revision = "0002_email_tables"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def _table_exists(bind, name: str) -> bool:
    return name in sa.inspect(bind).get_table_names()


def upgrade() -> None:
    bind = op.get_bind()

    if not _table_exists(bind, "scheduled_emails"):
        op.create_table(
            "scheduled_emails",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("to_addr", sa.String(), nullable=False),
            sa.Column("cc", sa.Text(), nullable=True),
            sa.Column("bcc", sa.Text(), nullable=True),
            sa.Column("subject", sa.Text(), nullable=True),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("in_reply_to", sa.Text(), nullable=True),
            sa.Column("references_hdr", sa.Text(), nullable=True),
            sa.Column("attachments", sa.Text(), nullable=True),
            sa.Column("send_at", sa.DateTime(), nullable=False),
            sa.Column("status", sa.String(), nullable=False, server_default="pending"),
            sa.Column("error", sa.Text(), nullable=True),
            sa.Column("owner", sa.String(), nullable=True, server_default=""),
            sa.Column("account_id", sa.String(), nullable=True),
            sa.Column("vhtna_kind", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_scheduled_emails_id", "scheduled_emails", ["id"])
        op.create_index("ix_scheduled_emails_send_at", "scheduled_emails", ["send_at"])
        op.create_index("ix_scheduled_emails_owner", "scheduled_emails", ["owner"])
        op.create_index("ix_scheduled_emails_account_id", "scheduled_emails", ["account_id"])
        op.create_index("ix_scheduled_emails_owner_status", "scheduled_emails", ["owner", "status"])

    if not _table_exists(bind, "email_summaries"):
        op.create_table(
            "email_summaries",
            sa.Column("message_id", sa.String(), nullable=False),
            sa.Column("uid", sa.String(), nullable=True),
            sa.Column("folder", sa.String(), nullable=True),
            sa.Column("subject", sa.Text(), nullable=True),
            sa.Column("sender", sa.Text(), nullable=True),
            sa.Column("summary", sa.Text(), nullable=False),
            sa.Column("model_used", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("message_id"),
        )

    if not _table_exists(bind, "email_ai_replies"):
        op.create_table(
            "email_ai_replies",
            sa.Column("message_id", sa.String(), nullable=False),
            sa.Column("uid", sa.String(), nullable=True),
            sa.Column("folder", sa.String(), nullable=True),
            sa.Column("reply", sa.Text(), nullable=False),
            sa.Column("model_used", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("message_id"),
        )

    if not _table_exists(bind, "email_tags"):
        op.create_table(
            "email_tags",
            sa.Column("message_id", sa.String(), nullable=False),
            sa.Column("owner", sa.String(), nullable=False, server_default=""),
            sa.Column("uid", sa.String(), nullable=True),
            sa.Column("folder", sa.String(), nullable=True),
            sa.Column("subject", sa.Text(), nullable=True),
            sa.Column("sender", sa.Text(), nullable=True),
            sa.Column("tags", sa.Text(), nullable=True),
            sa.Column("spam_verdict", sa.Integer(), nullable=True),
            sa.Column("spam_reason", sa.Text(), nullable=True),
            sa.Column("moved_to", sa.String(), nullable=True),
            sa.Column("model_used", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("message_id", "owner"),
        )

    if not _table_exists(bind, "email_calendar_extractions"):
        op.create_table(
            "email_calendar_extractions",
            sa.Column("message_id", sa.String(), nullable=False),
            sa.Column("uid", sa.String(), nullable=True),
            sa.Column("events_created", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("message_id"),
        )

    if not _table_exists(bind, "email_urgency_alerts"):
        op.create_table(
            "email_urgency_alerts",
            sa.Column("message_id", sa.String(), nullable=False),
            sa.Column("uid", sa.String(), nullable=True),
            sa.Column("folder", sa.String(), nullable=True),
            sa.Column("subject", sa.Text(), nullable=True),
            sa.Column("sender", sa.Text(), nullable=True),
            sa.Column("urgency", sa.String(), nullable=True),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("alerted", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("message_id"),
        )

    if not _table_exists(bind, "email_boundaries"):
        op.create_table(
            "email_boundaries",
            sa.Column("message_id", sa.String(), nullable=False),
            sa.Column("uid", sa.String(), nullable=True),
            sa.Column("folder", sa.String(), nullable=True),
            sa.Column("sig_start", sa.Integer(), nullable=True),
            sa.Column("quote_start", sa.Integer(), nullable=True),
            sa.Column("turns_json", sa.Text(), nullable=True),
            sa.Column("model_used", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("message_id"),
        )

    if not _table_exists(bind, "sender_signatures"):
        op.create_table(
            "sender_signatures",
            sa.Column("from_address", sa.String(), nullable=False),
            sa.Column("signature_text", sa.Text(), nullable=True),
            sa.Column("sample_count", sa.Integer(), nullable=True),
            sa.Column("last_built_at", sa.DateTime(), nullable=False),
            sa.Column("model_used", sa.String(), nullable=True),
            sa.Column("source", sa.String(), nullable=True),
            sa.PrimaryKeyConstraint("from_address"),
        )

    if not _table_exists(bind, "email_event_seen"):
        op.create_table(
            "email_event_seen",
            sa.Column("owner", sa.String(), nullable=False),
            sa.Column("account_key", sa.String(), nullable=False),
            sa.Column("folder", sa.String(), nullable=False),
            sa.Column("message_key", sa.String(), nullable=False),
            sa.Column("first_seen_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("owner", "account_key", "folder", "message_key"),
        )


def downgrade() -> None:
    for name in (
        "email_event_seen",
        "sender_signatures",
        "email_boundaries",
        "email_urgency_alerts",
        "email_calendar_extractions",
        "email_tags",
        "email_ai_replies",
        "email_summaries",
        "scheduled_emails",
    ):
        op.drop_table_if_exists(name) if hasattr(op, "drop_table_if_exists") else op.execute(
            f"DROP TABLE IF EXISTS {name}"
        )
