from sqlalchemy import select

from app.core.config import get_settings
from app.database.models import TarotCard
from app.database.session import AsyncSessionLocal
from app.services.tarot.cards import FULL_DECK, storage_image_path


async def ensure_tarot_cards_seeded() -> None:
    settings = get_settings()
    async with AsyncSessionLocal() as session:
        for card in FULL_DECK:
            image_path = storage_image_path(card, settings.tarot_cards_dir)
            existing = await session.scalar(select(TarotCard).where(TarotCard.slug == str(card["slug"])))
            if existing is None:
                session.add(
                    TarotCard(
                        slug=str(card["slug"]),
                        name=str(card["name"]),
                        arcana=str(card["arcana"]),
                        number=int(card["number"]),
                        description=str(card["description"]),
                        image_path=image_path,
                    )
                )
                continue

            existing.name = str(card["name"])
            existing.arcana = str(card["arcana"])
            existing.number = int(card["number"])
            existing.description = str(card["description"])
            existing.image_path = image_path

        await session.commit()
