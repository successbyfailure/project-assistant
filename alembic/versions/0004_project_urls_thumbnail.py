"""add project urls and thumbnail

Revision ID: 0004_project_urls_thumbnail
Revises: 0003_project_workspace_name
Create Date: 2026-01-30 00:00:00

"""

from alembic import op
import sqlalchemy as sa


revision = "0004_project_urls_thumbnail"
down_revision = "0003_project_workspace_name"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("production_url", sa.String(), nullable=True))
    op.add_column("projects", sa.Column("testing_url", sa.String(), nullable=True))
    op.add_column("projects", sa.Column("thumbnail_url", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "thumbnail_url")
    op.drop_column("projects", "testing_url")
    op.drop_column("projects", "production_url")
