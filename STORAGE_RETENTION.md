# ResuMesh Storage Retention and Soft Delete Policy

This document details the design and implementation of the **Soft Delete and Storage Retention** strategy for ResuMesh.

## 1. Objective

To preserve original uploaded resumes forever as the source of truth, enabling:
*   **Auditability:** Compliance with data retention laws and historical application tracking.
*   **Re-parsing:** Future structural changes or improved parser models can re-parse the original PDFs.
*   **Model Upgrades:** Newer embedding models (e.g. upgrading from 384 dimensions to 1536) can re-generate embeddings from the original files.
*   **Accidental Deletion Recovery:** Users can instantly recover their soft-deleted resumes.

---

## 2. Database Schema Changes

Two new columns and an index were added to the `resumes` table to support soft deletion:

```sql
-- Alter table to add soft delete flags
ALTER TABLE resumes ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE NOT NULL;
ALTER TABLE resumes ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE;

-- Create index for quick filtering of active resumes
CREATE INDEX IF NOT EXISTS resumes_user_id_is_deleted_idx ON resumes (user_id, is_deleted);
```

In the SQLAlchemy ORM model (`app/models/postgres_models.py`), these are represented as:
```python
is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
```

---

## 3. Soft Delete and Permanent Purge Workflow

When a deletion request is received on `DELETE /api/v1/resumes/{resume_id}`:

```
                  Delete Resume Request
                            ↓
             [Is permanent=true AND user is Admin?]
                /                            \
              YES                            NO
              /                                \
       [Hard Delete]                      [Soft Delete]
Delete file from Supabase Storage      Mark is_deleted = True
Remove record from PostgreSQL DB       Set deleted_at = CURRENT_TIMESTAMP
                                       Unset is_primary flag if it was primary
                                       Promote latest remaining resume to primary
                                       (PDF remains intact in Supabase Storage)
```

### API Implementation (`app/api/v1/endpoints/resumes.py`)
```python
@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resume(
    resume_id: str,
    permanent: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resume = ... # Owner/admin check
    
    if permanent:
        if current_user.role != 'admin':
            raise HTTPException(status_code=403, detail="Only admins can permanently delete resumes.")
            
        # Hard delete from Supabase storage and DB
        await storage_service.delete_file("resumes", resume.storage_path)
        await db.delete(resume)
    else:
        # Soft delete
        resume.is_deleted = True
        resume.deleted_at = datetime.now(timezone.utc)
        
        # Unset primary, promote latest remaining active resume
        if resume.is_primary:
            resume.is_primary = False
            ...
```

---

## 4. Resume Restore API

Soft-deleted resumes can be fully restored by their owner or an admin.

### Endpoint: `POST /api/v1/resumes/{resume_id}/restore`
*   **Behavior:** Reverts soft-deleted resumes back to active status (`is_deleted = False`, `deleted_at = None`).
*   **Primary Promotion:** If no other active resume is currently primary, the restored resume is promoted to primary.

---

## 5. Verification and Security Test Results

The storage retention system was verified via automated integration tests in `tests/test_production_hardening.py`:

*   `test_soft_delete_and_restore_flow`:
    1. Uploads a resume.
    2. Performs standard `DELETE`.
    3. Confirms the resume is hidden from list API but is visible when querying `include_deleted=true`.
    4. Calls `POST /restore` and verifies it appears in the active resume list again.
*   `test_admin_permanent_delete`:
    1. Uploads a resume.
    2. Verifies normal user gets `403 Forbidden` when attempting a permanent delete.
    3. Verifies admin successfully hard-deletes the resume from both database and storage.

**Test Status:** `PASSED`
