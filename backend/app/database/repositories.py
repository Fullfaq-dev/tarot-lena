from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

ModelT = TypeVar("ModelT")


class Repository(Generic[ModelT]):
    def __init__(self, session: AsyncSession, model: type[ModelT]) -> None:
        self.session = session
        self.model = model

    async def get(self, entity_id: str) -> ModelT | None:
        return await self.session.get(self.model, entity_id)

    async def list(self, limit: int = 100, offset: int = 0) -> list[ModelT]:
        result = await self.session.execute(select(self.model).limit(limit).offset(offset))
        return list(result.scalars())

    async def add(self, entity: ModelT) -> ModelT:
        self.session.add(entity)
        await self.session.flush()
        return entity
