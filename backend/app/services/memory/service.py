from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Memory, Message, RelationshipPerson, SoulProfile, User
from app.services.billing.limits import memory_limit_for_tier


class MemoryService:
    async def chat_memory(self, session: AsyncSession, user: User, tier: str) -> list[Message]:
        result = await session.execute(
            select(Message)
            .where(Message.user_id == user.id)
            .order_by(Message.created_at.desc())
            .limit(memory_limit_for_tier(tier))
        )
        return list(result.scalars())

    async def long_term_memory(self, session: AsyncSession, user: User, limit: int = 50) -> list[Memory]:
        result = await session.execute(
            select(Memory)
            .where(Memory.user_id == user.id)
            .where(Memory.is_active.is_(True))
            .order_by(Memory.importance.desc(), Memory.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars())

    async def relationship_memory(
        self, session: AsyncSession, user: User, limit: int = 50
    ) -> list[RelationshipPerson]:
        result = await session.execute(
            select(RelationshipPerson)
            .where(RelationshipPerson.user_id == user.id)
            .order_by(RelationshipPerson.importance.desc(), RelationshipPerson.updated_at.desc())
            .limit(limit)
        )
        return list(result.scalars())

    async def soul_profile(self, session: AsyncSession, user: User) -> SoulProfile | None:
        return await session.scalar(select(SoulProfile).where(SoulProfile.user_id == user.id))
