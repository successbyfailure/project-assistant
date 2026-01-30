"""add project workspace name

Revision ID: 0003_project_workspace_name
Revises: 0002_project_workspace_fields
Create Date: 2026-01-30 00:00:00

"""

from alembic import op
import sqlalchemy as sa


revision = "0003_project_workspace_name"
down_revision = "0002_project_workspace_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("workspace_name", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "workspace_name")
