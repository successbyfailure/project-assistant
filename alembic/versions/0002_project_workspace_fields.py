"""add project workspace fields

Revision ID: 0002_project_workspace_fields
Revises: 0001_initial
Create Date: 2026-01-30 00:00:00

"""

from alembic import op
import sqlalchemy as sa


revision = "0002_project_workspace_fields"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("workspace_id", sa.String(), nullable=True))
    op.add_column("projects", sa.Column("workspace_path", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "workspace_path")
    op.drop_column("projects", "workspace_id")
