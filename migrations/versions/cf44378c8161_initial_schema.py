"""Initial schema

Revision ID: cf44378c8161
Revises: 
Create Date: 2026-08-12 22:00:21.909024

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'cf44378c8161'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # 1. Independent parent tables first
    op.create_table('farms',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=150), nullable=False),
    sa.Column('code', sa.String(length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('code')
    )

    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=150), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('password_hash', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email')
    )

    op.create_table('sections',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('farm_id', sa.Integer(), nullable=False),
    sa.Column('code', sa.String(length=20), nullable=False),
    sa.Column('capacity', sa.Integer(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['farm_id'], ['farms.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('farm_id', 'code', name='uq_section_farm_code')
    )

    op.create_table('breeds',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('farm_id', sa.Integer(), nullable=True),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('expected_weight_min_kg', sa.Numeric(precision=5, scale=2), nullable=True),
    sa.Column('expected_weight_max_kg', sa.Numeric(precision=5, scale=2), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['farm_id'], ['farms.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('farm_id', 'name', name='uq_breed_farm_name')
    )

    op.create_table('herd_batches',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('farm_id', sa.Integer(), nullable=False),
    sa.Column('label', sa.String(length=100), nullable=True),
    sa.Column('week_start_date', sa.Date(), nullable=False),
    sa.Column('week_end_date', sa.Date(), nullable=False),
    sa.Column('male_count', sa.Integer(), nullable=False),
    sa.Column('female_count', sa.Integer(), nullable=False),
    sa.Column('avg_weight_kg', sa.Numeric(precision=5, scale=2), nullable=True),
    sa.Column('transferred_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['farm_id'], ['farms.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('herd_batches', schema=None) as batch_op:
        batch_op.create_index('idx_herd_batches_farm_week', ['farm_id', 'week_start_date'], unique=False)

    # 2. Tables dependent on farms/sections/breeds/users, but NOT rabbits yet
    op.create_table('farm_invites',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('farm_id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('role', sa.Enum('admin', 'user', name='farm_role'), nullable=False),
    sa.Column('token_hash', sa.Text(), nullable=False),
    sa.Column('invited_by', sa.Integer(), nullable=True),
    sa.Column('expires_at', sa.DateTime(), nullable=False),
    sa.Column('accepted_at', sa.DateTime(), nullable=True),
    sa.Column('cancelled_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['farm_id'], ['farms.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['invited_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('farm_invites', schema=None) as batch_op:
        batch_op.create_index('uq_farm_invites_pending', ['farm_id', 'email'], unique=True, postgresql_where=sa.text('accepted_at IS NULL AND cancelled_at IS NULL'))

    op.create_table('farm_users',
    sa.Column('farm_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('role', sa.Enum('admin', 'user', name='farm_role'), nullable=False),
    sa.Column('joined_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['farm_id'], ['farms.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('farm_id', 'user_id')
    )

    # 3. Create placeholder/minimal rabbits table or reorder so rabbits/litters don't break cyclic constraints. 
    # Wait: Rabbits reference litters, and litters reference rabbits! Let's handle the circular dependency safely.
    # To fix circular dependency between rabbits and litters, create 'rabbits' with nullable litter_id first, 
    # or create litters after rabbits. Looking closely: litters references rabbits (dam_id, sire_id), 
    # and rabbits references litters (litter_id). 
    # Standard fix: Create rabbits first (without litter_id foreign key or with nullable/deferred constraints), 
    # or create litters first without rabbit foreign keys? 
    # Actually, litters references rabbits(id) for dam_id/sire_id. Therefore, rabbits MUST exist before litters!
    
    op.create_table('rabbits',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('farm_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('role', sa.Enum('doe', 'buck', 'kit', name='rabbit_role'), nullable=False),
    sa.Column('status', sa.Enum('active', 'pregnant', 'nursing', 'resting', 'available', 'growing', 'ready_for_herd', 'for_sale', 'sold', 'transferred', 'deceased', name='rabbit_status'), nullable=False),
    sa.Column('breed_id', sa.Integer(), nullable=True),
    sa.Column('sex', sa.String(length=1), nullable=True),
    sa.Column('dam_id', sa.Integer(), nullable=True),
    sa.Column('sire_id', sa.Integer(), nullable=True),
    sa.Column('litter_id', sa.Integer(), nullable=True),
    sa.Column('hatch_date', sa.Date(), nullable=True),
    sa.Column('section_id', sa.Integer(), nullable=True),
    sa.Column('current_weight_kg', sa.Numeric(precision=5, scale=2), nullable=True),
    sa.Column('color_tag', sa.String(length=20), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['breed_id'], ['breeds.id'], ),
    sa.ForeignKeyConstraint(['dam_id'], ['rabbits.id'], ),
    sa.ForeignKeyConstraint(['farm_id'], ['farms.id'], ondelete='CASCADE'),
    # Note: litter_id reference to litters.id will be added via alter or litters created first. 
    # Since litters doesn't exist yet, let's omit the litters foreign key constraint here or create litters first.
    sa.ForeignKeyConstraint(['section_id'], ['sections.id'], ),
    sa.ForeignKeyConstraint(['sire_id'], ['rabbits.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('rabbits', schema=None) as batch_op:
        batch_op.create_index('idx_rabbits_dam', ['dam_id'], unique=False)
        batch_op.create_index('idx_rabbits_farm_role_status', ['farm_id', 'role', 'status'], unique=False)
        batch_op.create_index('idx_rabbits_litter', ['litter_id'], unique=False)

    # 4. Now create litters (rabbits table now exists for dam_id and sire_id)
    op.create_table('litters',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('farm_id', sa.Integer(), nullable=False),
    sa.Column('litter_number', sa.String(length=20), nullable=True),
    sa.Column('dam_id', sa.Integer(), nullable=False),
    sa.Column('sire_id', sa.Integer(), nullable=True),
    sa.Column('mating_date', sa.Date(), nullable=True),
    sa.Column('expected_nesting_date', sa.Date(), nullable=True),
    sa.Column('nest_box_added_at', sa.Date(), nullable=True),
    sa.Column('expected_birth_date', sa.Date(), nullable=True),
    sa.Column('expected_birth_date_latest', sa.Date(), nullable=True),
    sa.Column('actual_birth_date', sa.Date(), nullable=True),
    sa.Column('total_kits', sa.Integer(), nullable=False),
    sa.Column('male_kits', sa.Integer(), nullable=False),
    sa.Column('female_kits', sa.Integer(), nullable=False),
    sa.Column('kits_survived', sa.Integer(), nullable=True),
    sa.Column('herd_batch_id', sa.Integer(), nullable=True),
    sa.Column('status', sa.Enum('mating_recorded', 'expecting', 'nesting', 'born', 'nursing', 'weaning', 'ready_for_herd', 'transferred_to_herd', name='litter_status'), nullable=False),
    sa.Column('section_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['dam_id'], ['rabbits.id'], ),
    sa.ForeignKeyConstraint(['farm_id'], ['farms.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['herd_batch_id'], ['herd_batches.id'], ),
    sa.ForeignKeyConstraint(['section_id'], ['sections.id'], ),
    sa.ForeignKeyConstraint(['sire_id'], ['rabbits.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('farm_id', 'litter_number', name='uq_litter_farm_number')
    )
    with op.batch_alter_table('litters', schema=None) as batch_op:
        batch_op.create_index('idx_litters_farm_dam', ['farm_id', 'dam_id'], unique=False)
        batch_op.create_index('idx_litters_status', ['status'], unique=False)

    # 5. Add the foreign key for rabbits -> litters since litters now exists
    with op.batch_alter_table('rabbits', schema=None) as batch_op:
        batch_op.create_foreign_key('fk_rabbits_litter_id', 'litters', ['litter_id'], ['id'])

    # 6. Remaining dependent tables
    op.create_table('activity_logs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('farm_id', sa.Integer(), nullable=False),
    sa.Column('rabbit_id', sa.Integer(), nullable=True),
    sa.Column('litter_id', sa.Integer(), nullable=True),
    sa.Column('activity_type', sa.Enum('weight_check', 'routine_checkup', 'mating_event', 'nest_box_added', 'birth', 'transfer', 'health_note', 'status_change', 'sale', name='activity_type'), nullable=False),
    sa.Column('title', sa.String(length=150), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('occurred_at', sa.Date(), nullable=False),
    sa.Column('recorded_by', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.CheckConstraint('rabbit_id IS NOT NULL OR litter_id IS NOT NULL', name='ck_activity_has_subject'),
    sa.ForeignKeyConstraint(['farm_id'], ['farms.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['litter_id'], ['litters.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['rabbit_id'], ['rabbits.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['recorded_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('activity_logs', schema=None) as batch_op:
        batch_op.create_index('idx_activity_rabbit', ['rabbit_id', 'occurred_at'], unique=False)

    op.create_table('litter_milestones',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('litter_id', sa.Integer(), nullable=False),
    sa.Column('milestone', sa.Enum('birth', 'eyes_open', 'eating_solids', 'ready_for_herd', name='milestone_type'), nullable=False),
    sa.Column('expected_date', sa.Date(), nullable=True),
    sa.Column('actual_date', sa.Date(), nullable=True),
    sa.Column('completed', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['litter_id'], ['litters.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('litter_id', 'milestone', name='uq_milestone_per_litter')
    )

    op.create_table('weight_logs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('farm_id', sa.Integer(), nullable=False),
    sa.Column('rabbit_id', sa.Integer(), nullable=False),
    sa.Column('weight_kg', sa.Numeric(precision=5, scale=2), nullable=False),
    sa.Column('recorded_at', sa.Date(), nullable=False),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('recorded_by', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['farm_id'], ['farms.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['rabbit_id'], ['rabbits.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['recorded_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('weight_logs', schema=None) as batch_op:
        batch_op.create_index('idx_weight_logs_rabbit_date', ['rabbit_id', 'recorded_at'], unique=False)


def downgrade():
    with op.batch_alter_table('weight_logs', schema=None) as batch_op:
        batch_op.drop_index('idx_weight_logs_rabbit_date')

    op.drop_table('weight_logs')
    op.drop_table('litter_milestones')
    op.drop_table('activity_logs')
    
    with op.batch_alter_table('rabbits', schema=None) as batch_op:
        batch_op.drop_constraint('fk_rabbits_litter_id', type_='foreignkey')
        batch_op.drop_index('idx_rabbits_litter')
        batch_op.drop_index('idx_rabbits_farm_role_status')
        batch_op.drop_index('idx_rabbits_dam')

    op.drop_table('litters')
    op.drop_table('rabbits')
    
    with op.batch_alter_table('herd_batches', schema=None) as batch_op:
        batch_op.drop_index('idx_herd_batches_farm_week')

    op.drop_table('herd_batches')
    op.drop_table('breeds')
    
    with op.batch_alter_table('farm_invites', schema=None) as batch_op:
        batch_op.drop_index('uq_farm_invites_pending', postgresql_where=sa.text('accepted_at IS NULL AND cancelled_at IS NULL'))

    op.drop_table('farm_invites')
    op.drop_table('farm_users')
    op.drop_table('sections')
    op.drop_table('users')
    op.drop_table('farms')