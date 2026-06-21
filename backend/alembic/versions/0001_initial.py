"""Initial database migration

Revision ID: 0001_initial
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users ─────────────────────────────────────────────────────────────────
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('role', sa.String(50), nullable=False, server_default='user'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('headline', sa.String(255), nullable=True),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('location', sa.String(255), nullable=True),
        sa.Column('linkedin_url', sa.String(500), nullable=True),
        sa.Column('github_url', sa.String(500), nullable=True),
        sa.Column('portfolio_url', sa.String(500), nullable=True),
        sa.Column('avatar_url', sa.String(500), nullable=True),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # ── resumes ───────────────────────────────────────────────────────────────
    op.create_table(
        'resumes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('file_name', sa.String(500), nullable=False),
        sa.Column('file_path', sa.String(1000), nullable=False),
        sa.Column('file_type', sa.String(20), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=True),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_parsed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('embedding_id', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_resumes_user_id', 'resumes', ['user_id'])

    # ── parsed_resumes ─────────────────────────────────────────────────────────
    op.create_table(
        'parsed_resumes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('resume_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('linkedin', sa.String(500), nullable=True),
        sa.Column('github', sa.String(500), nullable=True),
        sa.Column('location', sa.String(255), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('skills', postgresql.JSONB(), nullable=True),
        sa.Column('experience', postgresql.JSONB(), nullable=True),
        sa.Column('education', postgresql.JSONB(), nullable=True),
        sa.Column('projects', postgresql.JSONB(), nullable=True),
        sa.Column('certifications', postgresql.JSONB(), nullable=True),
        sa.Column('languages', postgresql.JSONB(), nullable=True),
        sa.Column('total_years_experience', sa.Float(), nullable=True),
        sa.Column('seniority_level', sa.String(50), nullable=True),
        sa.Column('raw_text', sa.Text(), nullable=True),
        sa.Column('parsing_model', sa.String(100), nullable=True),
        sa.Column('parsing_confidence', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['resume_id'], ['resumes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('resume_id'),
    )

    # ── jobs ───────────────────────────────────────────────────────────────────
    op.create_table(
        'jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('company', sa.String(255), nullable=False),
        sa.Column('location', sa.String(255), nullable=True),
        sa.Column('job_type', sa.String(100), nullable=True),
        sa.Column('portal', sa.String(100), nullable=False, server_default='manual'),
        sa.Column('portal_job_id', sa.String(255), nullable=True),
        sa.Column('job_url', sa.String(2000), nullable=True),
        sa.Column('raw_description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_jobs_portal', 'jobs', ['portal'])
    op.create_index('ix_jobs_company', 'jobs', ['company'])

    # ── job_descriptions ───────────────────────────────────────────────────────
    op.create_table(
        'job_descriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('required_skills', postgresql.JSONB(), nullable=True),
        sa.Column('preferred_skills', postgresql.JSONB(), nullable=True),
        sa.Column('tech_stack', postgresql.JSONB(), nullable=True),
        sa.Column('soft_skills', postgresql.JSONB(), nullable=True),
        sa.Column('responsibilities', postgresql.JSONB(), nullable=True),
        sa.Column('qualifications', postgresql.JSONB(), nullable=True),
        sa.Column('education_requirements', postgresql.JSONB(), nullable=True),
        sa.Column('certifications', postgresql.JSONB(), nullable=True),
        sa.Column('min_years_experience', sa.Float(), nullable=True),
        sa.Column('max_years_experience', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('job_id'),
    )

    # ── applications ───────────────────────────────────────────────────────────
    op.create_table(
        'applications',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('resume_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='saved'),
        sa.Column('match_score', sa.Float(), nullable=True),
        sa.Column('matched_skills', postgresql.JSONB(), nullable=True),
        sa.Column('missing_skills', postgresql.JSONB(), nullable=True),
        sa.Column('recommendations', postgresql.JSONB(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('applied_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('interview_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('offer_amount', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['resume_id'], ['resumes.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_applications_user_id', 'applications', ['user_id'])
    op.create_index('ix_applications_status', 'applications', ['status'])

    # ── cover_letters ──────────────────────────────────────────────────────────
    op.create_table(
        'cover_letters',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('tone', sa.String(50), nullable=True),
        sa.Column('word_count', sa.Integer(), nullable=True),
        sa.Column('is_ai_generated', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('llm_model_used', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_cover_letters_user_id', 'cover_letters', ['user_id'])

    # ── feedback ───────────────────────────────────────────────────────────────
    op.create_table(
        'feedback',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('application_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('feedback_type', sa.String(100), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )

    # ── audit_logs ─────────────────────────────────────────────────────────────
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(255), nullable=False),
        sa.Column('resource_type', sa.String(100), nullable=True),
        sa.Column('resource_id', sa.String(255), nullable=True),
        sa.Column('ip_address', sa.String(50), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('feedback')
    op.drop_table('cover_letters')
    op.drop_table('applications')
    op.drop_table('job_descriptions')
    op.drop_table('jobs')
    op.drop_table('parsed_resumes')
    op.drop_table('resumes')
    op.drop_table('users')
