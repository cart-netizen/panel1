"""Добавление таблицы user_preferences

Revision ID: 003
Revises: 002
Create Date: 2025-08-15
"""

from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
  op.create_table(
    'user_preferences',
    sa.Column('id', sa.Integer(), primary_key=True),
    sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, unique=True),
    sa.Column('favorite_numbers', sa.Text(), default='{"field1": [], "field2": []}'),
    sa.Column('default_lottery', sa.String(50), default='4x20'),
    sa.Column('preferred_strategies', sa.Text(), default='[]'),
    sa.Column('notification_settings', sa.Text(), default='{}'),
    sa.Column('action_history', sa.Text(), default='[]'),
    sa.Column('created_at', sa.DateTime(), default=datetime.utcnow),
    sa.Column('updated_at', sa.DateTime(), default=datetime.utcnow),
  )

  op.create_index('ix_user_preferences_user_id', 'user_preferences', ['user_id'])


def downgrade():
  op.drop_index('ix_user_preferences_user_id')
  op.drop_table('user_preferences')