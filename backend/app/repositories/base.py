from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Generic CRUD repository for SQLAlchemy models."""

    def __init__(self, model: Type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db

    async def get(self, id: Union[UUID, str]) -> Optional[ModelType]:
        """Get a single record by UUID or UUID string."""
        if isinstance(id, str):
            try:
                id = UUID(id)
            except ValueError:
                return None
        result = await self.db.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_multi(self, *, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Get multiple records with offset and limit."""
        result = await self.db.execute(
            select(self.model).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def create(self, db_obj: ModelType) -> ModelType:
        """Add a new object to the database session."""
        self.db.add(db_obj)
        await self.db.flush()
        return db_obj

    async def update(self, db_obj: ModelType, obj_in: Dict[str, Any]) -> ModelType:
        """Update fields of an existing model instance."""
        for field, value in obj_in.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        self.db.add(db_obj)
        await self.db.flush()
        return db_obj

    async def delete(self, db_obj: ModelType) -> None:
        """Delete an object from the database session."""
        await self.db.delete(db_obj)
        await self.db.flush()
