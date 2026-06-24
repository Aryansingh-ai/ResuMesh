# ResuMesh SHA256 Duplicate Detection Audit

This document details the implementation of the **SHA256 File Hashing and Duplicate Upload Detection** service for ResuMesh.

## 1. Objective

To prevent duplicate uploads, save cloud storage costs, and eliminate redundant embedding generations and LLM parsing requests. The system detects when a user uploads a file they have already uploaded and instantly returns the existing record.

---

## 2. Database Schema Changes

A new column and index were added to the `resumes` table to support fast hash lookups:

```sql
-- Alter table to add hash support
ALTER TABLE resumes ADD COLUMN IF NOT EXISTS file_hash VARCHAR(64);

-- Create a B-Tree index for quick duplicate checks
CREATE INDEX IF NOT EXISTS resumes_file_hash_idx ON resumes (file_hash);
```

In the SQLAlchemy ORM model (`app/models/postgres_models.py`), this is represented as:
```python
file_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
```

---

## 3. Hashing and Duplicate Detection Workflow

The duplicate detection workflow operates as follows:

```
Resume Upload (PDF/DOCX)
           ↓
Read raw file bytes in memory
           ↓
Compute SHA256 hash of file content
           ↓
Check DB for active, non-deleted resume for the current user matching the hash
           ↓
    [Hash Found?]
      /        \
    YES         NO
    /             \
Return existing    Generate unique ID & Storage path
Resume ID & Meta   Upload file to Supabase Storage bucket
(Skip storage      Create new database record (version + 1)
 & parsing)        Unset previous primary flags
                   Queue background LLM parsing & pgvector indexing
```

### API Implementation Details (`app/api/v1/endpoints/resumes.py`)
```python
# Compute SHA256 hash
file_hash = hashlib.sha256(content).hexdigest()

# Check for existing active resume for this user with identical hash
dup_result = await db.execute(
    select(Resume).where(
        Resume.user_id == current_user.id,
        Resume.file_hash == file_hash,
        Resume.is_deleted == False
    )
)
duplicate_resume = dup_result.scalar_one_or_none()
if duplicate_resume:
    logger.info("Duplicate resume uploaded, returning existing resume", resume_id=str(duplicate_resume.id))
    return {
        "id": str(duplicate_resume.id),
        "title": duplicate_resume.title,
        "file_name": duplicate_resume.file_name,
        "is_primary": duplicate_resume.is_primary,
        "version": duplicate_resume.version,
        "message": "Duplicate file detected. Returning existing resume ID.",
        ...
    }
```

---

## 4. Self-Healing Backfill Migration

To support existing resumes in the database, a self-healing migration script `apply_hardening_migration.py` was executed. The script:
1. Queries all resumes where `file_hash` is NULL.
2. Downloads each file from Supabase Storage in memory.
3. Computes the SHA256 hash of the file.
4. Backfills the `file_hash` column and sets the initial `version = 1`.

### Migration Performance Logs
During execution, 5 pre-existing resumes were successfully backfilled:
```
Starting self-healing hash backfill migration for existing resumes...
Found 5 resumes without SHA256 file hash.
Downloading file to compute hash: Aryan Singh Resume.pdf (ID: 6d1fa57e-0697-4fb1-a125-850ecb28dfad)
Success: Hash computed: 83a14af371e85d174e6711c3b84dd8020f0055591bf5302568654faf3b244836
...
Backfill finished. Successfully backfilled: 5, Errors: 0.
```

---

## 5. Verification and Security Test Results

The duplicate detection was validated via automated integration tests in `tests/test_production_hardening.py`:

```python
async def test_duplicate_resume_upload(self, client: AsyncClient, auth_headers: dict):
    file_content = b"This is the unique content of resume one."
    
    # Upload 1
    resp1 = await client.post("/api/v1/resumes/upload", files={"file": ("resume.pdf", file_content)}, headers=auth_headers["user_a"])
    resume_id_1 = resp1.json()["id"]

    # Upload 2 (same content)
    resp2 = await client.post("/api/v1/resumes/upload", files={"file": ("copy.pdf", file_content)}, headers=auth_headers["user_a"])
    resume_id_2 = resp2.json()["id"]

    assert resume_id_1 == resume_id_2
    assert "Duplicate file detected" in resp2.json()["message"]
```

**Test Status:** `PASSED`
