"""Привязать старые файлы из static/generated к сообщениям vision в БД."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import select

from app.core.config import get_settings
from app.database.models import Message, UsageRecord
from app.database.session import AsyncSessionLocal


def _photo_files(storage_dir: Path) -> list[Path]:
    if not storage_dir.exists():
        return []
    return sorted(
        (
            path
            for path in storage_dir.iterdir()
            if path.is_file() and path.name != ".gitkeep"
        ),
        key=lambda path: path.stat().st_mtime,
    )


def _file_mtime(path: Path) -> datetime:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)


def _public_url(filename: str) -> str:
    settings = get_settings()
    return f"{settings.public_base_url.rstrip('/')}/static/generated/{filename}"


def _match_files_to_messages(
    files: list[Path],
    messages: list[Message],
    *,
    max_delta_sec: float = 180.0,
) -> list[tuple[Message, Path]]:
    unused = list(files)
    pairs: list[tuple[Message, Path]] = []

    for message in sorted(messages, key=lambda item: item.created_at):
        if message.created_at is None or not unused:
            break

        msg_time = message.created_at
        if msg_time.tzinfo is None:
            msg_time = msg_time.replace(tzinfo=UTC)

        best_file: Path | None = None
        best_delta: float | None = None
        for file_path in unused:
            delta = abs((_file_mtime(file_path) - msg_time).total_seconds())
            if best_delta is None or delta < best_delta:
                best_delta = delta
                best_file = file_path

        if best_file is None or best_delta is None or best_delta > max_delta_sec:
            continue

        pairs.append((message, best_file))
        unused.remove(best_file)

    return pairs


async def backfill_vision_photo_urls(*, dry_run: bool = False) -> dict[str, int]:
    settings = get_settings()
    files = _photo_files(settings.media_storage_dir)

    async with AsyncSessionLocal() as session:
        result = await session.scalars(select(Message).order_by(Message.created_at))
        all_messages = list(result)

        vision_user_messages = [
            message
            for message in all_messages
            if message.role == "user"
            and (message.meta or {}).get("has_image")
            and not (message.meta or {}).get("source_image_url")
        ]

        pairs = _match_files_to_messages(files, vision_user_messages)
        stats = {
            "files_on_disk": len(files),
            "vision_messages": len(vision_user_messages),
            "matched_messages": 0,
            "matched_usage": 0,
            "matched_assistant": 0,
        }

        for user_message, file_path in pairs:
            url = _public_url(file_path.name)
            stats["matched_messages"] += 1

            if dry_run:
                print(f"[dry-run] message {user_message.id} -> {url}")
                continue

            meta = dict(user_message.meta or {})
            meta["source_image_url"] = url
            user_message.meta = meta

            msg_time = user_message.created_at
            if msg_time and msg_time.tzinfo is None:
                msg_time = msg_time.replace(tzinfo=UTC)

            window_start = msg_time - timedelta(seconds=30) if msg_time else None
            window_end = msg_time + timedelta(minutes=10) if msg_time else None

            usage_rows = await session.scalars(
                select(UsageRecord)
                .where(UsageRecord.user_id == user_message.user_id)
                .where(UsageRecord.feature.like("vision_%"))
                .order_by(UsageRecord.created_at)
            )
            for usage in usage_rows:
                if (usage.meta or {}).get("source_image_url"):
                    continue
                usage_time = usage.created_at
                if usage_time and usage_time.tzinfo is None:
                    usage_time = usage_time.replace(tzinfo=UTC)
                if (
                    msg_time
                    and usage_time
                    and window_start
                    and window_end
                    and window_start <= usage_time <= window_end
                ):
                    usage_meta = dict(usage.meta or {})
                    usage_meta["source_image_url"] = url
                    if meta.get("vision_mode"):
                        usage_meta["vision_mode"] = meta["vision_mode"]
                    usage.meta = usage_meta
                    stats["matched_usage"] += 1
                    break

            for assistant in all_messages:
                if assistant.user_id != user_message.user_id or assistant.role != "assistant":
                    continue
                if (assistant.meta or {}).get("source_image_url"):
                    continue
                assistant_time = assistant.created_at
                if assistant_time and assistant_time.tzinfo is None:
                    assistant_time = assistant_time.replace(tzinfo=UTC)
                if (
                    not msg_time
                    or not assistant_time
                    or assistant_time < msg_time
                    or (assistant_time - msg_time).total_seconds() > 600
                ):
                    continue
                feature = (assistant.meta or {}).get("feature", "")
                if not str(feature).startswith("vision_"):
                    continue
                assistant_meta = dict(assistant.meta or {})
                assistant_meta["source_image_url"] = url
                assistant.meta = assistant_meta
                stats["matched_assistant"] += 1
                break

        if not dry_run:
            await session.commit()

        return stats


async def _main() -> None:
    import sys

    dry_run = "--dry-run" in sys.argv
    stats = await backfill_vision_photo_urls(dry_run=dry_run)
    print(stats)


if __name__ == "__main__":
    asyncio.run(_main())
