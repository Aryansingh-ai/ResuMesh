-- ==========================================
-- SUPABASE ROW-LEVEL SECURITY (RLS) MIGRATION
-- Project: ResuMesh Production Hardening
-- ==========================================

-- 1. Enable Row Level Security (RLS) on all 12 Tables
ALTER TABLE IF EXISTS public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.resumes ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.parsed_resumes ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.job_descriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.applications ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.cover_letters ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.recommendations ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.experiments ENABLE ROW LEVEL SECURITY;

-- ==========================================
-- 2. CREATE DATABASE POLICIES
-- ==========================================

-- --- 2.1 USERS TABLE POLICIES ---
-- Users can read/update only their own profile; admins can access all profiles.
DROP POLICY IF EXISTS users_policy ON public.users;
CREATE POLICY users_policy ON public.users
    FOR ALL
    USING (
        id = auth.uid() 
        OR (SELECT role::text FROM public.users WHERE id = auth.uid()) = 'admin'
    );

-- --- 2.2 RESUMES TABLE POLICIES ---
-- Users can read/insert/update/delete only their own resumes; admins can access all.
DROP POLICY IF EXISTS resumes_user_policy ON public.resumes;
CREATE POLICY resumes_user_policy ON public.resumes
    FOR ALL
    USING (
        user_id = auth.uid() 
        OR (SELECT role::text FROM public.users WHERE id = auth.uid()) = 'admin'
    );

-- --- 2.3 PARSED_RESUMES TABLE POLICIES ---
-- Users can access parsed resumes only for resumes they own; admins can access all.
DROP POLICY IF EXISTS parsed_resumes_user_policy ON public.parsed_resumes;
CREATE POLICY parsed_resumes_user_policy ON public.parsed_resumes
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM public.resumes 
            WHERE resumes.id = resume_id 
              AND resumes.user_id = auth.uid()
        )
        OR (SELECT role::text FROM public.users WHERE id = auth.uid()) = 'admin'
    );

-- --- 2.4 EMBEDDINGS TABLE POLICIES ---
-- Users can access embeddings only for resumes they own; admins can access all embeddings.
DROP POLICY IF EXISTS embeddings_policy ON public.embeddings;
CREATE POLICY embeddings_policy ON public.embeddings
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM public.resumes 
            WHERE resumes.id = resume_id 
              AND resumes.user_id = auth.uid()
        )
        OR (SELECT role::text FROM public.users WHERE id = auth.uid()) = 'admin'
    );

-- --- 2.5 JOBS TABLE POLICIES ---
-- Recruiters/admins can create/modify/delete jobs; all authenticated users can read jobs.
DROP POLICY IF EXISTS jobs_read_policy ON public.jobs;
CREATE POLICY jobs_read_policy ON public.jobs
    FOR SELECT
    USING (auth.role() = 'authenticated');

DROP POLICY IF EXISTS jobs_write_policy ON public.jobs;
CREATE POLICY jobs_write_policy ON public.jobs
    FOR ALL
    USING (
        (SELECT role::text FROM public.users WHERE id = auth.uid()) IN ('admin', 'recruiter')
    );

-- --- 2.6 JOB_DESCRIPTIONS TABLE POLICIES ---
-- Recruiters/admins can create/modify/delete descriptions; all authenticated users can read.
DROP POLICY IF EXISTS job_descriptions_read_policy ON public.job_descriptions;
CREATE POLICY job_descriptions_read_policy ON public.job_descriptions
    FOR SELECT
    USING (auth.role() = 'authenticated');

DROP POLICY IF EXISTS job_descriptions_write_policy ON public.job_descriptions;
CREATE POLICY job_descriptions_write_policy ON public.job_descriptions
    FOR ALL
    USING (
        (SELECT role::text FROM public.users WHERE id = auth.uid()) IN ('admin', 'recruiter')
    );

-- --- 2.7 APPLICATIONS TABLE POLICIES ---
-- Users can access only their own applications; admins can access all applications.
DROP POLICY IF EXISTS applications_user_policy ON public.applications;
CREATE POLICY applications_user_policy ON public.applications
    FOR ALL
    USING (
        user_id = auth.uid() 
        OR (SELECT role::text FROM public.users WHERE id = auth.uid()) = 'admin'
    );

-- --- 2.8 COVER_LETTERS TABLE POLICIES ---
-- Users can access only their own cover letters; admins can access all.
DROP POLICY IF EXISTS cover_letters_policy ON public.cover_letters;
CREATE POLICY cover_letters_policy ON public.cover_letters
    FOR ALL
    USING (
        user_id = auth.uid() 
        OR (SELECT role::text FROM public.users WHERE id = auth.uid()) = 'admin'
    );

-- --- 2.9 FEEDBACK TABLE POLICIES ---
-- Users can access only their own feedback; admins can access all.
DROP POLICY IF EXISTS feedback_policy ON public.feedback;
CREATE POLICY feedback_policy ON public.feedback
    FOR ALL
    USING (
        user_id = auth.uid() 
        OR (SELECT role::text FROM public.users WHERE id = auth.uid()) = 'admin'
    );

-- --- 2.10 RECOMMENDATIONS TABLE POLICIES ---
-- Users can access only their own recommendations; admins can access all.
DROP POLICY IF EXISTS recommendations_policy ON public.recommendations;
CREATE POLICY recommendations_policy ON public.recommendations
    FOR ALL
    USING (
        user_id = auth.uid() 
        OR (SELECT role::text FROM public.users WHERE id = auth.uid()) = 'admin'
    );

-- --- 2.11 AUDIT_LOGS TABLE POLICIES ---
-- Only administrators are allowed to read, write, or modify audit logs.
DROP POLICY IF EXISTS audit_logs_policy ON public.audit_logs;
CREATE POLICY audit_logs_policy ON public.audit_logs
    FOR ALL
    USING (
        (SELECT role::text FROM public.users WHERE id = auth.uid()) = 'admin'
    );

-- --- 2.12 EXPERIMENTS TABLE POLICIES ---
-- Only administrators are allowed to read, write, or modify experiments.
DROP POLICY IF EXISTS experiments_policy ON public.experiments;
CREATE POLICY experiments_policy ON public.experiments
    FOR ALL
    USING (
        (SELECT role::text FROM public.users WHERE id = auth.uid()) = 'admin'
    );


-- ==========================================
-- 3. SUPABASE STORAGE BUCKET POLICIES
-- ==========================================

-- --- 3.1 Upload (INSERT) Policy ---
-- Allows authenticated users to upload files only to their own directory inside the 'resumes' bucket.
-- Directory path structure: resumes/<user_id>/<filename>
DROP POLICY IF EXISTS "Allow users to upload their own resumes" ON storage.objects;
CREATE POLICY "Allow users to upload their own resumes" ON storage.objects
    FOR INSERT
    WITH CHECK (
        bucket_id = 'resumes' 
        AND (storage.foldername(name))[1] = auth.uid()::text
    );

-- --- 3.2 Read (SELECT) Policy ---
-- Allows users to read resumes in their own folder, and admins to read all resumes.
DROP POLICY IF EXISTS "Allow users to read their own resumes" ON storage.objects;
CREATE POLICY "Allow users to read their own resumes" ON storage.objects
    FOR SELECT
    USING (
        bucket_id = 'resumes' 
        AND (
            (storage.foldername(name))[1] = auth.uid()::text 
            OR (SELECT role::text FROM public.users WHERE id = auth.uid()) = 'admin'
        )
    );

-- --- 3.3 Delete (DELETE) Policy ---
-- Allows users to delete resumes in their own folder, and admins to delete any resume.
DROP POLICY IF EXISTS "Allow users to delete their own resumes" ON storage.objects;
CREATE POLICY "Allow users to delete their own resumes" ON storage.objects
    FOR DELETE
    USING (
        bucket_id = 'resumes' 
        AND (
            (storage.foldername(name))[1] = auth.uid()::text 
            OR (SELECT role::text FROM public.users WHERE id = auth.uid()) = 'admin'
        )
    );
