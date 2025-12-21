"""Add campaign_image field to campaigns table

Revision ID: 001_add_campaign_image
Revises: 
Create Date: 2025-12-21 21:06:58.155678

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_add_campaign_image'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add campaign_image column to campaigns table."""
    op.add_column('campaigns', sa.Column('campaign_image', sa.String(length=1024), nullable=True))


def downgrade() -> None:
    """Remove campaign_image column from campaigns table."""
    op.drop_column('campaigns', 'campaign_image')
