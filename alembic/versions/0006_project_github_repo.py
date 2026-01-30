"""add project github_repo

Revision ID: 0006_project_github_repo
Revises: 0005_project_workspace_ref
Create Date: 2026-01-30 00:00:00

"""

from alembic import op
import sqlalchemy as sa


revision = "0006_project_github_repo"
down_revision = "0005_project_workspace_ref"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("github_repo", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "github_repo")
