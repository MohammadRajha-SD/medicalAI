"""Initial 

Revision ID: 6008b27b4d65
Revises: 
Create Date: 2024-04-22 16:42:44.716903

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6008b27b4d65'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('chat', schema=None) as batch_op:
        batch_op.drop_column('patient_id')
        batch_op.drop_column('timestamp')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('chat', schema=None) as batch_op:
        batch_op.add_column(sa.Column('timestamp', sa.DATETIME(), nullable=True))
        batch_op.add_column(sa.Column('patient_id', sa.INTEGER(), nullable=False))

    # ### end Alembic commands ###