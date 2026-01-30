"""add project codespace fields

Revision ID: 0007_project_codespace_fields
Revises: 0006_project_github_repo
Create Date: 2026-01-30 00:00:00

"""

from alembic import op
import sqlalchemy as sa


revision = "0007_project_codespace_fields"
down_revision = "0006_project_github_repo"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("codespace_id", sa.String(), nullable=True))
    op.add_column("projects", sa.Column("codespace_name", sa.String(), nullable=True))
    op.add_column("projects", sa.Column("codespace_url", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "codespace_url")
    op.drop_column("projects", "codespace_name")
    op.drop_column("projects", "codespace_id")
