"""
Seed script to create an admin user and sample data for development.
Run once after migrations: python scripts/seed.py
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))


async def seed():
    from app.core.database import AsyncSessionLocal, init_db
    from app.core.security import hash_password
    from app.models.user import User
    from app.models.job import Job, JobDescription
    from sqlalchemy import select
    import uuid

    await init_db()

    async with AsyncSessionLocal() as session:
        # Check if admin already exists
        result = await session.execute(select(User).where(User.email == 'admin@resumesh.dev'))
        existing = result.scalar_one_or_none()

        if existing:
            print("✓ Admin user already exists")
        else:
            admin = User(
                id=uuid.uuid4(),
                email='admin@resumesh.dev',
                hashed_password=hash_password('Admin1234!'),
                full_name='ResuMesh Admin',
                role='admin',
                is_active=True,
                is_verified=True,
            )
            session.add(admin)

            demo = User(
                id=uuid.uuid4(),
                email='demo@resumesh.dev',
                hashed_password=hash_password('Demo1234!'),
                full_name='Demo User',
                role='user',
                is_active=True,
                is_verified=True,
            )
            session.add(demo)
            await session.commit()
            print("✓ Created admin: admin@resumesh.dev / Admin1234!")
            print("✓ Created demo:  demo@resumesh.dev  / Demo1234!")

    print("\n✅ Seed complete.")


if __name__ == '__main__':
    asyncio.run(seed())
