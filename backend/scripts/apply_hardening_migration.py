import os
import sys
import asyncio
import hashlib
import uuid
from pathlib import Path
import structlog

# Add backend directory to sys.path
backend_dir = Path(__file__).parent.parent.resolve()
sys.path.append(str(backend_dir))

# Set environmental variable to load the correct .env
os.environ["ENV_FILE"] = str(backend_dir / ".env")

from sqlalchemy import text, select
from app.core.config import settings
from app.core.database import engine, AsyncSessionLocal
from app.models.postgres_models import Resume
from app.services.supabase_storage import get_storage_service

logger = structlog.get_logger(__name__)

async def run_migration():
    print("--- Starting Production Hardening Migration ---")
    
    # 1. Execute DDL to alter tables and create indexes
    async with engine.begin() as conn:
        print("Altering tables and creating database indexes...")
        
        # Alter table resumes (split into single statements)
        await conn.execute(text("ALTER TABLE resumes ADD COLUMN IF NOT EXISTS file_hash VARCHAR(64);"))
        await conn.execute(text("ALTER TABLE resumes ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE NOT NULL;"))
        await conn.execute(text("ALTER TABLE resumes ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE;"))
        await conn.execute(text("ALTER TABLE resumes ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1 NOT NULL;"))
        
        # Create standard index for resumes
        await conn.execute(text("CREATE INDEX IF NOT EXISTS resumes_file_hash_idx ON resumes (file_hash);"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS resumes_user_id_is_deleted_idx ON resumes (user_id, is_deleted);"))

        # Enable pgvector HNSW index
        print("Creating pgvector HNSW indexes...")
        try:
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS embeddings_hnsw_idx 
                ON embeddings 
                USING hnsw (embedding vector_cosine_ops);
            """))
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS jobs_hnsw_idx 
                ON jobs 
                USING hnsw (embedding vector_cosine_ops);
            """))
            print("Successfully created HNSW indexes.")
        except Exception as e:
            logger.warning("Failed to create HNSW indexes. Verify if pgvector version >= 0.5.0", error=str(e))
            print(f"Warning: Failed to create HNSW indexes: {str(e)}")

        # 2. Implement Database Row Level Security (RLS)
        print("Enabling Row Level Security (RLS) and policies...")
        
        # Enable RLS
        await conn.execute(text("ALTER TABLE resumes ENABLE ROW LEVEL SECURITY;"))
        await conn.execute(text("ALTER TABLE parsed_resumes ENABLE ROW LEVEL SECURITY;"))
        await conn.execute(text("ALTER TABLE applications ENABLE ROW LEVEL SECURITY;"))
        
        # Create or replace tables RLS policies
        # Resumes table policy
        await conn.execute(text("DROP POLICY IF EXISTS resumes_user_policy ON resumes;"))
        await conn.execute(text("""
            CREATE POLICY resumes_user_policy ON resumes
            FOR ALL
            USING (user_id = auth.uid() OR (SELECT role FROM public.users WHERE id = auth.uid()) = 'admin');
        """))
        
        # Parsed resumes table policy
        await conn.execute(text("DROP POLICY IF EXISTS parsed_resumes_user_policy ON parsed_resumes;"))
        await conn.execute(text("""
            CREATE POLICY parsed_resumes_user_policy ON parsed_resumes
            FOR ALL
            USING (
                EXISTS (SELECT 1 FROM public.resumes WHERE resumes.id = resume_id AND resumes.user_id = auth.uid())
                OR (SELECT role FROM public.users WHERE id = auth.uid()) = 'admin'
            );
        """))

        # Applications table policy
        await conn.execute(text("DROP POLICY IF EXISTS applications_user_policy ON applications;"))
        await conn.execute(text("""
            CREATE POLICY applications_user_policy ON applications
            FOR ALL
            USING (user_id = auth.uid() OR (SELECT role FROM public.users WHERE id = auth.uid()) = 'admin');
        """))

        # 3. Implement Supabase Storage RLS Policies
        print("Deploying storage RLS policies...")
        # Insert
        await conn.execute(text("DROP POLICY IF EXISTS \"Allow users to upload their own resumes\" ON storage.objects;"))
        await conn.execute(text("""
            CREATE POLICY "Allow users to upload their own resumes" ON storage.objects
            FOR INSERT
            WITH CHECK (bucket_id = 'resumes' AND (storage.foldername(name))[1] = auth.uid()::text);
        """))

        # Select
        await conn.execute(text("DROP POLICY IF EXISTS \"Allow users to read their own resumes\" ON storage.objects;"))
        await conn.execute(text("""
            CREATE POLICY "Allow users to read their own resumes" ON storage.objects
            FOR SELECT
            USING (bucket_id = 'resumes' AND ((storage.foldername(name))[1] = auth.uid()::text OR (SELECT role FROM public.users WHERE id = auth.uid()) = 'admin'));
        """))

        # Delete
        await conn.execute(text("DROP POLICY IF EXISTS \"Allow users to delete their own resumes\" ON storage.objects;"))
        await conn.execute(text("""
            CREATE POLICY "Allow users to delete their own resumes" ON storage.objects
            FOR DELETE
            USING (bucket_id = 'resumes' AND ((storage.foldername(name))[1] = auth.uid()::text OR (SELECT role FROM public.users WHERE id = auth.uid()) = 'admin'));
        """))

    print("Database structure migration complete.")

    # 4. Self-healing migration for existing resumes (compute & backfill file_hash)
    print("\nStarting self-healing hash backfill migration for existing resumes...")
    storage_service = get_storage_service()
    
    async with AsyncSessionLocal() as session:
        # Get all resumes with null file_hash
        res = await session.execute(select(Resume).where(Resume.file_hash == None))
        resumes = res.scalars().all()
        print(f"Found {len(resumes)} resumes without SHA256 file hash.")
        
        migrated_count = 0
        errors_count = 0
        
        for resume in resumes:
            try:
                print(f"Downloading file to compute hash: {resume.file_name} (ID: {resume.id})")
                content = await storage_service.download_file("resumes", resume.storage_path)
                
                # Compute SHA256 hash
                h = hashlib.sha256(content).hexdigest()
                resume.file_hash = h
                # Set initial version for migrated resumes
                resume.version = 1
                
                migrated_count += 1
                print(f"Success: Hash computed: {h}")
            except Exception as ex:
                errors_count += 1
                logger.error("Failed to backfill hash", id=str(resume.id), error=str(ex))
                print(f"Error backfilling hash for resume {resume.id}: {str(ex)}")
                
        await session.commit()
        print(f"Backfill finished. Successfully backfilled: {migrated_count}, Errors: {errors_count}.")
        
    print("\n--- Hardening Migration Finished Successfully ---")

if __name__ == "__main__":
    asyncio.run(run_migration())

