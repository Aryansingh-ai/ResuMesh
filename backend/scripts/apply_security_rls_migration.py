import os
import sys
import asyncio
import structlog
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).parent.parent.resolve()
sys.path.append(str(backend_dir))

# Set environmental variable to load the correct .env
os.environ["ENV_FILE"] = str(backend_dir / ".env")

from sqlalchemy import text
from app.core.database import engine

logger = structlog.get_logger(__name__)

async def run_security_migration():
    print("--- Starting Supabase RLS Security Migration ---")
    
    async with engine.begin() as conn:
        print("Enabling Row Level Security (RLS) on tables...")
        
        tables = [
            "experiments",
            "jobs",
            "job_descriptions",
            "audit_logs",
            "embeddings",
            "users",
            "cover_letters",
            "feedback",
            "recommendations"
        ]
        
        # 1. Enable RLS on all tables
        for table in tables:
            try:
                print(f"Enabling RLS on table '{table}'...")
                await conn.execute(text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;"))
                print(f"RLS enabled on '{table}'.")
            except Exception as e:
                print(f"Error enabling RLS on '{table}': {str(e)}")
                logger.error("Failed to enable RLS", table=table, error=str(e))
        
        # 2. Deploy RLS Policies
        print("\nDeploying policies...")

        # --- USERS table ---
        # Users can read/update only their own profile; admins can access all profiles.
        print("Deploying policies for 'users'...")
        await conn.execute(text("DROP POLICY IF EXISTS users_policy ON users;"))
        await conn.execute(text("""
            CREATE POLICY users_policy ON users
            FOR ALL
            USING (id = auth.uid() OR (SELECT role::text FROM public.users WHERE id = auth.uid()) = 'admin');
        """))

        # --- EMBEDDINGS table ---
        # Users can access embeddings only for resumes they own; admins can access all embeddings.
        print("Deploying policies for 'embeddings'...")
        await conn.execute(text("DROP POLICY IF EXISTS embeddings_policy ON embeddings;"))
        await conn.execute(text("""
            CREATE POLICY embeddings_policy ON embeddings
            FOR ALL
            USING (
                EXISTS (SELECT 1 FROM public.resumes WHERE resumes.id = resume_id AND resumes.user_id = auth.uid())
                OR (SELECT role::text FROM public.users WHERE id = auth.uid()) = 'admin'
            );
        """))

        # --- JOBS table ---
        # Recruiters/admins can create/modify jobs; authenticated users can read jobs.
        print("Deploying policies for 'jobs'...")
        await conn.execute(text("DROP POLICY IF EXISTS jobs_read_policy ON jobs;"))
        await conn.execute(text("""
            CREATE POLICY jobs_read_policy ON jobs
            FOR SELECT
            USING (auth.role() = 'authenticated');
        """))
        await conn.execute(text("DROP POLICY IF EXISTS jobs_write_policy ON jobs;"))
        await conn.execute(text("""
            CREATE POLICY jobs_write_policy ON jobs
            FOR ALL
            USING ((SELECT role::text FROM public.users WHERE id = auth.uid()) IN ('admin', 'recruiter'));
        """))

        # --- JOB_DESCRIPTIONS table ---
        # Authenticated read; recruiter/admin write.
        print("Deploying policies for 'job_descriptions'...")
        await conn.execute(text("DROP POLICY IF EXISTS job_descriptions_read_policy ON job_descriptions;"))
        await conn.execute(text("""
            CREATE POLICY job_descriptions_read_policy ON job_descriptions
            FOR SELECT
            USING (auth.role() = 'authenticated');
        """))
        await conn.execute(text("DROP POLICY IF EXISTS job_descriptions_write_policy ON job_descriptions;"))
        await conn.execute(text("""
            CREATE POLICY job_descriptions_write_policy ON job_descriptions
            FOR ALL
            USING ((SELECT role::text FROM public.users WHERE id = auth.uid()) IN ('admin', 'recruiter'));
        """))

        # --- AUDIT_LOGS table ---
        # Admin only.
        print("Deploying policies for 'audit_logs'...")
        await conn.execute(text("DROP POLICY IF EXISTS audit_logs_policy ON audit_logs;"))
        await conn.execute(text("""
            CREATE POLICY audit_logs_policy ON audit_logs
            FOR ALL
            USING ((SELECT role::text FROM public.users WHERE id = auth.uid()) = 'admin');
        """))

        # --- FEEDBACK table ---
        # User can access only their own feedback.
        print("Deploying policies for 'feedback'...")
        await conn.execute(text("DROP POLICY IF EXISTS feedback_policy ON feedback;"))
        await conn.execute(text("""
            CREATE POLICY feedback_policy ON feedback
            FOR ALL
            USING (user_id = auth.uid() OR (SELECT role::text FROM public.users WHERE id = auth.uid()) = 'admin');
        """))

        # --- RECOMMENDATIONS table ---
        # User can access only their own recommendations.
        print("Deploying policies for 'recommendations'...")
        await conn.execute(text("DROP POLICY IF EXISTS recommendations_policy ON recommendations;"))
        await conn.execute(text("""
            CREATE POLICY recommendations_policy ON recommendations
            FOR ALL
            USING (user_id = auth.uid() OR (SELECT role::text FROM public.users WHERE id = auth.uid()) = 'admin');
        """))

        # --- COVER_LETTERS table ---
        # User can access only their own cover letters.
        print("Deploying policies for 'cover_letters'...")
        await conn.execute(text("DROP POLICY IF EXISTS cover_letters_policy ON cover_letters;"))
        await conn.execute(text("""
            CREATE POLICY cover_letters_policy ON cover_letters
            FOR ALL
            USING (user_id = auth.uid() OR (SELECT role::text FROM public.users WHERE id = auth.uid()) = 'admin');
        """))

        # --- EXPERIMENTS table ---
        # Admin only.
        print("Deploying policies for 'experiments'...")
        await conn.execute(text("DROP POLICY IF EXISTS experiments_policy ON experiments;"))
        await conn.execute(text("""
            CREATE POLICY experiments_policy ON experiments
            FOR ALL
            USING ((SELECT role::text FROM public.users WHERE id = auth.uid()) = 'admin');
        """))

    print("\n--- RLS Security Migration Finished Successfully ---")

if __name__ == "__main__":
    asyncio.run(run_security_migration())
