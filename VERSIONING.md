# ResuMesh Resume Versioning and Primary Promotion

This document details the design and implementation of the **Resume Versioning and Primary Resume Toggling** system for ResuMesh.

## 1. Objective

To allow users to maintain multiple versions of their resume (e.g. V1, V2, V3) as they update their experience and skills, while ensuring that recruiters and the matching engine use their latest or designated primary resume by default.

---

## 2. Database Schema Changes

Two new columns were added to the `resumes` table to support versioning and primary status:

```sql
-- Alter table to add versioning columns
ALTER TABLE resumes ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1 NOT NULL;
ALTER TABLE resumes ADD COLUMN IF NOT EXISTS is_primary BOOLEAN DEFAULT FALSE NOT NULL;
```

In the SQLAlchemy ORM model (`app/models/postgres_models.py`), these are represented as:
```python
version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
```

---

## 3. Versioning and Primary Selection Logic

### A. New Upload Workflow
When a user uploads a resume file with a **new** hash:
1. The backend queries the database for the highest version number among the user's resumes (including soft-deleted ones):
   ```sql
   SELECT MAX(version) FROM resumes WHERE user_id = :user_id;
   ```
2. The new resume is assigned `version = max_version + 1`.
3. The new resume automatically becomes the **primary** resume (`is_primary = True`).
4. All other resumes belonging to the user are automatically updated to `is_primary = False`.

### B. Upload Implementation (`app/api/v1/endpoints/resumes.py`)
```python
# Fetch max version for this user's resumes to determine next version
version_result = await db.execute(
    select(Resume.version)
    .where(Resume.user_id == current_user.id)
    .order_by(Resume.version.desc())
    .limit(1)
)
max_version = version_result.scalar() or 0
new_version = max_version + 1

# Force this new version to automatically become primary (unset others)
await db.execute(
    update(Resume)
    .where(Resume.user_id == current_user.id)
    .values(is_primary=False)
)

# Save new resume record with version=new_version and is_primary=True
```

---

## 4. Primary Resume Switching API

Users can explicitly switch their active primary resume at any time.

### Endpoint: `POST /api/v1/resumes/{resume_id}/primary`
*   **Access:** Owners of the resume or admin users.
*   **Behavior:** Unsets the primary flag on all resumes for the owner, and sets `is_primary = True` on the requested resume.

### API Code:
```python
@router.post("/{resume_id}/primary")
async def set_primary_resume(
    resume_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Fetch resume checking tenant boundary
    resume = ... # Owner/admin verification
    
    if resume.is_deleted:
        raise HTTPException(status_code=400, detail="Cannot set a deleted resume as primary")

    # Unset current primary for the owner of this resume
    await db.execute(
        update(Resume)
        .where(Resume.user_id == resume.user_id)
        .values(is_primary=False)
    )

    resume.is_primary = True
    await db.commit()
    return {"message": "Resume set as primary successfully"}
```

---

## 5. Verification and Security Test Results

The versioning and primary promotion system was verified via automated integration tests in `tests/test_production_hardening.py`:

```python
async def test_versioning_on_different_uploads(self, client: AsyncClient, auth_headers: dict):
    # Upload V1
    resp1 = await client.post("/api/v1/resumes/upload", files={"file": ("v1.pdf", b"Content V1")}, data={"title": "V1"}, headers=auth_headers["user_a"])
    res1 = resp1.json()
    assert res1["version"] == 1
    assert res1["is_primary"] is True

    # Upload V2 (modified content)
    resp2 = await client.post("/api/v1/resumes/upload", files={"file": ("v2.pdf", b"Content V2")}, data={"title": "V2"}, headers=auth_headers["user_a"])
    res2 = resp2.json()
    assert res2["version"] == 2
    assert res2["is_primary"] is True

    # Verify V1 is no longer primary, V2 is primary
    list_resp = await client.get("/api/v1/resumes/", headers=auth_headers["user_a"])
    ...
```

**Test Status:** `PASSED`
