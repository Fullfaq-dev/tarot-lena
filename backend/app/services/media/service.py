from sqlalchemy import select

from app.database.models import MediaJob, MediaJobStatus
from app.database.session import AsyncSessionLocal


class MediaJobService:
    async def create_job(self, kind: str, payload: dict, user_id: str | None = None) -> MediaJob:
        async with AsyncSessionLocal() as session:
            provider_task_id = payload.get("provider_task_id")
            clean_payload = {key: value for key, value in payload.items() if key != "provider_task_id"}
            job = MediaJob(
                user_id=user_id,
                kind=kind,
                input_payload=clean_payload,
                provider_task_id=provider_task_id,
            )
            session.add(job)
            await session.commit()
            await session.refresh(job)
            return job

    async def handle_callback(self, payload: dict) -> None:
        task_id = payload.get("taskId") or payload.get("task_id") or payload.get("id")
        if not task_id:
            return

        async with AsyncSessionLocal() as session:
            result = await session.execute(select(MediaJob).where(MediaJob.provider_task_id == task_id))
            job = result.scalar_one_or_none()
            if job is None:
                return
            status = str(payload.get("status", "")).lower()
            job.status = (
                MediaJobStatus.SUCCEEDED.value
                if status in {"success", "succeeded", "completed"}
                else MediaJobStatus.FAILED.value
                if status in {"failed", "error"}
                else MediaJobStatus.RUNNING.value
            )
            job.result_payload = payload
            await session.commit()
