"""Initial schema — all tables.

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision: str = "001"
down_revision: str | None = None
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


# ---------------------------------------------------------------------------
# Enum type definitions
# We create them explicitly so Alembic can drop them cleanly on downgrade.
# ---------------------------------------------------------------------------

userrole_enum = postgresql.ENUM(
    "admin", "operator", "readonly",
    name="userrole",
    create_type=False,
)

camerastatus_enum = postgresql.ENUM(
    "active", "inactive",
    name="camerastatus",
    create_type=False,
)

linedirection_enum = postgresql.ENUM(
    "entry", "exit", "both",
    name="linedirection",
    create_type=False,
)

eventdirection_enum = postgresql.ENUM(
    "entry", "exit",
    name="eventdirection",
    create_type=False,
)

eventstatus_enum = postgresql.ENUM(
    "automatic", "corrected", "removed",
    name="eventstatus",
    create_type=False,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_enums() -> None:
    bind = op.get_bind()
    for enum in (
        userrole_enum,
        camerastatus_enum,
        linedirection_enum,
        eventdirection_enum,
        eventstatus_enum,
    ):
        enum.create(bind, checkfirst=True)


def _drop_enums() -> None:
    bind = op.get_bind()
    for enum in (
        eventstatus_enum,
        eventdirection_enum,
        linedirection_enum,
        camerastatus_enum,
        userrole_enum,
    ):
        enum.drop(bind, checkfirst=True)


# ---------------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------------

def upgrade() -> None:
    _create_enums()

    # ------------------------------------------------------------------
    # users
    # ------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=True),
        sa.Column(
            "role",
            sa.Enum("admin", "operator", "readonly", name="userrole"),
            nullable=False,
            server_default="admin",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ------------------------------------------------------------------
    # cameras
    # ------------------------------------------------------------------
    op.create_table(
        "cameras",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("rtsp_url_encrypted", sa.String(), nullable=False),
        sa.Column("username_encrypted", sa.String(), nullable=True),
        sa.Column("password_encrypted", sa.String(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("active", "inactive", name="camerastatus"),
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "processing_fps",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("5"),
        ),
        sa.Column(
            "processing_width",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("640"),
        ),
        sa.Column(
            "processing_height",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("480"),
        ),
        sa.Column(
            "min_confidence",
            sa.Float(),
            nullable=False,
            server_default=sa.text("0.5"),
        ),
        sa.Column(
            "is_online",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # ------------------------------------------------------------------
    # camera_counting_lines
    # ------------------------------------------------------------------
    op.create_table(
        "camera_counting_lines",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "camera_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cameras.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("x1_relative", sa.Float(), nullable=False),
        sa.Column("y1_relative", sa.Float(), nullable=False),
        sa.Column("x2_relative", sa.Float(), nullable=False),
        sa.Column("y2_relative", sa.Float(), nullable=False),
        sa.Column(
            "direction",
            sa.Enum("entry", "exit", "both", name="linedirection"),
            nullable=False,
            server_default="both",
        ),
        sa.Column(
            "active_classes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text('\'["car","truck","bus","motorcycle"]\'::jsonb'),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_camera_counting_lines_camera_id",
        "camera_counting_lines",
        ["camera_id"],
    )

    # ------------------------------------------------------------------
    # vehicle_events
    # ------------------------------------------------------------------
    op.create_table(
        "vehicle_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "camera_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cameras.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("vehicle_type", sa.String(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column(
            "direction",
            sa.Enum("entry", "exit", name="eventdirection"),
            nullable=True,
        ),
        sa.Column("tracker_id", sa.Integer(), nullable=True),
        sa.Column("bbox_x1", sa.Float(), nullable=True),
        sa.Column("bbox_y1", sa.Float(), nullable=True),
        sa.Column("bbox_x2", sa.Float(), nullable=True),
        sa.Column("bbox_y2", sa.Float(), nullable=True),
        sa.Column("snapshot_path", sa.String(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("automatic", "corrected", "removed", name="eventstatus"),
            nullable=False,
            server_default="automatic",
        ),
        sa.Column("observation", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_vehicle_events_camera_id",
        "vehicle_events",
        ["camera_id"],
    )
    op.create_index(
        "ix_vehicle_events_event_time",
        "vehicle_events",
        ["event_time"],
    )
    op.create_index(
        "ix_vehicle_events_camera_event_time",
        "vehicle_events",
        ["camera_id", "event_time"],
    )

    # ------------------------------------------------------------------
    # manual_adjustments
    # ------------------------------------------------------------------
    op.create_table(
        "manual_adjustments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "event_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("vehicle_events.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column(
            "previous_value",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "new_value",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_manual_adjustments_event_id",
        "manual_adjustments",
        ["event_id"],
    )
    op.create_index(
        "ix_manual_adjustments_user_id",
        "manual_adjustments",
        ["user_id"],
    )

    # ------------------------------------------------------------------
    # system_logs
    # ------------------------------------------------------------------
    op.create_table(
        "system_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("level", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # ------------------------------------------------------------------
    # app_settings
    # ------------------------------------------------------------------
    op.create_table(
        "app_settings",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column(
            "value",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column(
            "updated_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_app_settings_key", "app_settings", ["key"], unique=True)
    op.create_index("ix_app_settings_updated_by", "app_settings", ["updated_by"])


# ---------------------------------------------------------------------------
# Downgrade
# ---------------------------------------------------------------------------

def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_index("ix_app_settings_updated_by", table_name="app_settings")
    op.drop_index("ix_app_settings_key", table_name="app_settings")
    op.drop_table("app_settings")

    op.drop_table("system_logs")

    op.drop_index("ix_manual_adjustments_user_id", table_name="manual_adjustments")
    op.drop_index("ix_manual_adjustments_event_id", table_name="manual_adjustments")
    op.drop_table("manual_adjustments")

    op.drop_index("ix_vehicle_events_camera_event_time", table_name="vehicle_events")
    op.drop_index("ix_vehicle_events_event_time", table_name="vehicle_events")
    op.drop_index("ix_vehicle_events_camera_id", table_name="vehicle_events")
    op.drop_table("vehicle_events")

    op.drop_index(
        "ix_camera_counting_lines_camera_id", table_name="camera_counting_lines"
    )
    op.drop_table("camera_counting_lines")
    op.drop_table("cameras")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    _drop_enums()
