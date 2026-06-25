"""
Quick diagnostic: test the full cover letter endpoint flow against real DB.
Run: venv\Scripts\python.exe backend\scripts\debug_cover_letter.py
"""
import asyncio
import sys
import os

sys.path.insert(0, ".")

async def main():
    from app.core.database import AsyncSessionLocal
    from sqlalchemy import select, text
    from app.models.postgres_models import Resume, ParsedResume, Job, JobDescription, CoverLetter

    print("=" * 60)
    print("COVER LETTER DEBUG")
    print("=" * 60)

    async with AsyncSessionLocal() as db:
        # 1. Check resumes
        res = await db.execute(
            select(Resume).where(Resume.is_deleted == False).limit(3)
        )
        resumes = res.scalars().all()
        print(f"\n[1] Resumes found: {len(resumes)}")
        for r in resumes:
            print(f"    - {r.id} | {r.title} | parsed={r.is_parsed}")

        if not resumes:
            print("    PROBLEM: No resumes. Upload a resume first.")
            return

        resume = resumes[0]

        # 2. Check parsed resume
        pres = await db.execute(
            select(ParsedResume).where(ParsedResume.resume_id == resume.id)
        )
        parsed = pres.scalar_one_or_none()
        print(f"\n[2] ParsedResume: {'FOUND' if parsed else 'MISSING'}")
        if parsed:
            print(f"    full_name={parsed.full_name}")
            print(f"    total_years_experience={parsed.total_years_experience}")

        if not parsed:
            print("    PROBLEM: Resume is not yet parsed. Wait for background task.")
            return

        # 3. Check jobs
        jres = await db.execute(select(Job).limit(3))
        jobs = jres.scalars().all()
        print(f"\n[3] Jobs found: {len(jobs)}")
        for j in jobs:
            uid = getattr(j, "user_id", "no-user_id-column")
            print(f"    - {j.id} | {j.title} @ {j.company} | user_id={uid}")

        if not jobs:
            print("    PROBLEM: No jobs. Analyze a job first.")
            return

        job = jobs[0]

        # 4. Check job description
        jdres = await db.execute(
            select(JobDescription).where(JobDescription.job_id == job.id)
        )
        jd = jdres.scalar_one_or_none()
        print(f"\n[4] JobDescription: {'FOUND' if jd else 'MISSING (OK, optional)'}")
        if jd:
            print(f"    required_skills={jd.required_skills}")

        # 5. Try saving a CoverLetter record
        print("\n[5] Attempting to save CoverLetter to DB...")
        try:
            cl = CoverLetter(
                user_id=resume.user_id,
                title="DEBUG Test Cover Letter",
                content="This is a test cover letter content.",
                tone="professional",
                word_count=7,
                is_ai_generated=True,
                llm_model_used="groq",
            )
            db.add(cl)
            await db.commit()
            print(f"    SUCCESS: saved id={cl.id}")
            await db.delete(cl)
            await db.commit()
            print("    Cleaned up test record.")
        except Exception as e:
            print(f"    ERROR: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()

        # 6. Test generation
        print("\n[6] Testing LLM generation...")
        try:
            from app.services.cover_letter_generator import CoverLetterGenerator
            gen = CoverLetterGenerator()
            skills = parsed.skills or {}
            all_skills = []
            for sl in skills.values():
                all_skills.extend(sl or [])
            resume_data = {
                "full_name": parsed.full_name,
                "skills": parsed.skills or {},
                "experience": parsed.experience or [],
                "total_years_experience": parsed.total_years_experience or 0,
            }
            job_data = {
                "title": job.title,
                "company": job.company,
                "location": job.location,
                "required_skills": (jd.required_skills if jd else []) or [],
            }
            content = await gen.generate(resume_data=resume_data, job_data=job_data, tone="professional")
            print(f"    SUCCESS: {len(content)} chars generated")
            print(f"    Preview: {content[:150]}...")
        except Exception as e:
            print(f"    ERROR: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    print("DIAGNOSIS COMPLETE")
    print("=" * 60)


asyncio.run(main())
