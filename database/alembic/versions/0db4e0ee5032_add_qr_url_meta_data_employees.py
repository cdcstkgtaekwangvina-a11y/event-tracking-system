"""add qr_url, meta_data to employees

Revision ID: 0db4e0ee5032
Revises: 9b581d297bb2
Create Date: 2026-08-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0db4e0ee5032'
down_revision: Union[str, Sequence[str], None] = '9b581d297bb2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'employees',
        sa.Column('qr_url', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    op.add_column(
        'employees',
        sa.Column(
            'meta_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('employees', 'meta_data')
    op.drop_column('employees', 'qr_url')
