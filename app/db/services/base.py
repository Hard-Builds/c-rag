from typing import Any, Dict, Generic, List, Optional, Type, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

ModelType = TypeVar("ModelType")


class BaseDB(Generic[ModelType]):
    def __init__(self, db: AsyncSession, model: Type[ModelType]):
        self.db = db
        self.model = model

    async def get_by_id(self, id: int | UUID) -> Optional[ModelType]:
        return await self.db.get(self.model, id)

    async def get_all(self) -> List[ModelType]:
        result = await self.db.execute(select(self.model))
        return list(result.scalars().all())

    async def get_by_filter(self, **filters: Any) -> Optional[ModelType]:
        stmt = select(self.model).filter_by(**filters)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_by_where(self, *expressions) -> Optional[ModelType]:
        stmt = select(self.model).where(*expressions)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_all_by_filter(self, **filters: Any) -> List[ModelType]:
        stmt = select(self.model).filter_by(**filters)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, obj_in: Dict[str, Any], commit: bool = True) -> ModelType:
        obj = self.model(**obj_in)
        self.db.add(obj)
        await self.db.flush()
        if commit:
            await self.db.commit()
            await self.db.refresh(obj)
        return obj

    async def create_many(self, objs_in: List[Dict[str, Any]], commit: bool = True) -> List[ModelType]:
        objs = [self.model(**obj) for obj in objs_in]
        self.db.add_all(objs)
        await self.db.flush()
        if commit:
            await self.db.commit()
            for obj in objs:
                await self.db.refresh(obj)
        return objs

    async def update(self, _id: int | UUID, obj_in: Dict[str, Any],
                     commit: bool = True) -> Optional[ModelType]:
        db_obj = await self.db.get(self.model, _id)
        if db_obj is None:
            return None
        for key, value in obj_in.items():
            setattr(db_obj, key, value)
        if commit:
            await self.db.commit()
            await self.db.refresh(db_obj)
        return db_obj

    async def delete_by_id(self, id: int | UUID) -> Optional[ModelType]:
        obj = await self.db.get(self.model, id)
        if obj:
            await self.db.delete(obj)
            await self.db.commit()
        return obj

    async def delete_all_by_filter(self, **filters: Any) -> int:
        stmt = select(self.model)
        for field, value in filters.items():
            stmt = stmt.where(getattr(self.model, field) == value)
        result = await self.db.execute(stmt)
        objs = result.scalars().all()
        for obj in objs:
            await self.db.delete(obj)
        await self.db.commit()
        return len(objs)
