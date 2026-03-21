"""align_models_with_api_contract

Revision ID: 2e60989aee55
Revises: b3c7a1d2e4f5
Create Date: 2026-03-22 00:17:01.316303

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2e60989aee55'
down_revision: Union[str, None] = 'b3c7a1d2e4f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- New tables ---
    op.create_table('fee_line_items',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('fee_structure_id', sa.String(length=36), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('amount', sa.Float(), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('is_optional', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['fee_structure_id'], ['fee_structures.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('guardians',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('student_id', sa.String(length=36), nullable=False),
    sa.Column('first_name', sa.String(length=100), nullable=False),
    sa.Column('last_name', sa.String(length=100), nullable=False),
    sa.Column('relationship', sa.String(length=50), nullable=False),
    sa.Column('phone', sa.String(length=50), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=True),
    sa.Column('is_primary', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['student_id'], ['students.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('payment_timeline',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('payment_id', sa.String(length=36), nullable=False),
    sa.Column('event', sa.String(length=100), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['payment_id'], ['payments.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    # --- ADD COLUMN operations (SQLite supports these) ---
    op.add_column('audit_logs', sa.Column('ip_address', sa.String(length=50), nullable=True))
    op.add_column('audit_logs', sa.Column('user_agent', sa.Text(), nullable=True))
    op.add_column('fee_structures', sa.Column('grades_json', sa.Text(), nullable=True))
    op.add_column('fee_structures', sa.Column('status', sa.String(length=20), server_default='DRAFT', nullable=False))
    op.add_column('fee_structures', sa.Column('version', sa.Integer(), server_default='1', nullable=False))
    op.add_column('fee_structures', sa.Column('published_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('payments', sa.Column('channel', sa.String(length=50), nullable=True))
    op.add_column('payments', sa.Column('provider', sa.String(length=100), nullable=True))
    op.add_column('payments', sa.Column('payer_name', sa.String(length=200), nullable=True))
    op.add_column('payments', sa.Column('payer_phone', sa.String(length=50), nullable=True))
    op.add_column('payments', sa.Column('payer_email', sa.String(length=255), nullable=True))
    op.add_column('payments', sa.Column('receipt_number', sa.String(length=100), nullable=True))
    op.add_column('payments', sa.Column('currency', sa.String(length=10), server_default='USD', nullable=False))
    op.add_column('payments', sa.Column('metadata_json', sa.Text(), nullable=True))
    op.add_column('reminder_configs', sa.Column('timing', sa.String(length=20), nullable=True))
    op.add_column('reminder_configs', sa.Column('channels_json', sa.Text(), nullable=True))
    op.add_column('reminder_configs', sa.Column('audience', sa.String(length=20), server_default='ALL', nullable=False))
    op.add_column('reminder_configs', sa.Column('grades_json', sa.Text(), nullable=True))
    op.add_column('reminder_configs', sa.Column('student_ids_json', sa.Text(), nullable=True))
    op.add_column('reminder_configs', sa.Column('message_template', sa.Text(), nullable=True))
    op.add_column('reminder_configs', sa.Column('days_offset', sa.Integer(), nullable=True))
    op.add_column('reminder_history', sa.Column('config_name', sa.String(length=200), nullable=True))
    op.add_column('reminder_history', sa.Column('recipient_count', sa.Integer(), server_default='0', nullable=False))
    op.add_column('reminder_history', sa.Column('delivered_count', sa.Integer(), server_default='0', nullable=False))
    op.add_column('reminder_history', sa.Column('failed_count', sa.Integer(), server_default='0', nullable=False))
    op.add_column('reminder_history', sa.Column('channels_json', sa.Text(), nullable=True))
    op.add_column('schools', sa.Column('city', sa.String(length=100), nullable=True))
    op.add_column('schools', sa.Column('state', sa.String(length=100), nullable=True))
    op.add_column('schools', sa.Column('country', sa.String(length=100), nullable=True))
    op.add_column('schools', sa.Column('receipt_footer', sa.Text(), nullable=True))
    op.add_column('schools', sa.Column('merchant_code', sa.String(length=100), nullable=True))
    op.add_column('schools', sa.Column('biller_code', sa.String(length=100), nullable=True))
    op.add_column('schools', sa.Column('account_identifier', sa.String(length=100), nullable=True))
    op.add_column('schools', sa.Column('academic_term_config', sa.Text(), nullable=True))
    op.add_column('student_invoices', sa.Column('currency', sa.String(length=10), server_default='USD', nullable=False))
    op.add_column('students', sa.Column('student_id', sa.String(length=50), nullable=True))
    op.add_column('students', sa.Column('class_name', sa.String(length=100), nullable=True))
    op.add_column('students', sa.Column('date_of_birth', sa.String(length=20), nullable=True))
    op.add_column('students', sa.Column('enrollment_date', sa.String(length=20), nullable=True))
    op.add_column('students', sa.Column('balance', sa.Float(), server_default='0', nullable=False))
    op.add_column('users', sa.Column('avatar_url', sa.String(length=500), nullable=True))
    op.add_column('users', sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True))

    # NOTE: Skipping alter_column and create_unique_constraint operations
    # that are not supported by SQLite. These constraints already exist
    # correctly from the RBAC migration, or will be enforced at the
    # application level. For PostgreSQL deployments, the model definitions
    # enforce the correct constraints on fresh databases.


def downgrade() -> None:
    op.drop_column('users', 'last_login_at')
    op.drop_column('users', 'avatar_url')
    op.drop_column('students', 'balance')
    op.drop_column('students', 'enrollment_date')
    op.drop_column('students', 'date_of_birth')
    op.drop_column('students', 'class_name')
    op.drop_column('students', 'student_id')
    op.drop_column('student_invoices', 'currency')
    op.drop_column('schools', 'academic_term_config')
    op.drop_column('schools', 'account_identifier')
    op.drop_column('schools', 'biller_code')
    op.drop_column('schools', 'merchant_code')
    op.drop_column('schools', 'receipt_footer')
    op.drop_column('schools', 'country')
    op.drop_column('schools', 'state')
    op.drop_column('schools', 'city')
    op.drop_column('reminder_history', 'channels_json')
    op.drop_column('reminder_history', 'failed_count')
    op.drop_column('reminder_history', 'delivered_count')
    op.drop_column('reminder_history', 'recipient_count')
    op.drop_column('reminder_history', 'config_name')
    op.drop_column('reminder_configs', 'days_offset')
    op.drop_column('reminder_configs', 'message_template')
    op.drop_column('reminder_configs', 'student_ids_json')
    op.drop_column('reminder_configs', 'grades_json')
    op.drop_column('reminder_configs', 'audience')
    op.drop_column('reminder_configs', 'channels_json')
    op.drop_column('reminder_configs', 'timing')
    op.drop_column('payments', 'metadata_json')
    op.drop_column('payments', 'currency')
    op.drop_column('payments', 'receipt_number')
    op.drop_column('payments', 'payer_email')
    op.drop_column('payments', 'payer_phone')
    op.drop_column('payments', 'payer_name')
    op.drop_column('payments', 'provider')
    op.drop_column('payments', 'channel')
    op.drop_column('fee_structures', 'published_at')
    op.drop_column('fee_structures', 'version')
    op.drop_column('fee_structures', 'status')
    op.drop_column('fee_structures', 'grades_json')
    op.drop_column('audit_logs', 'user_agent')
    op.drop_column('audit_logs', 'ip_address')
    op.drop_table('payment_timeline')
    op.drop_table('guardians')
    op.drop_table('fee_line_items')
