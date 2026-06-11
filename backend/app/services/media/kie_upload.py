import logging
from pathlib import Path

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class KieFileUpload:
    """Upload files to KIE CDN — required for STT/TTS and image-to-image input URLs."""

    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.settings.kie_api_key}"}

    @property
    def base_url(self) -> str:
        return self.settings.kie_file_upload_base_url.rstrip("/")

    async def ensure_kie_url(
        self,
        *,
        local_path: Path | None = None,
        source_url: str | None = None,
        upload_path: str = "telegram",
        file_name: str | None = None,
    ) -> str:
        if self.settings.kie_api_key == "replace-me":
            if source_url:
                return source_url
            raise ValueError("KIE API key не настроен")

        if local_path and local_path.exists():
            try:
                return await self.upload_stream(
                    local_path,
                    upload_path=upload_path,
                    file_name=file_name or local_path.name,
                )
            except Exception as exc:
                logger.warning("KIE stream upload failed path=%s: %s", local_path, exc)

        if source_url:
            try:
                return await self.upload_from_url(
                    source_url,
                    upload_path=upload_path,
                    file_name=file_name,
                )
            except Exception as exc:
                logger.warning("KIE url upload failed url=%s: %s", source_url, exc)
                return source_url

        raise ValueError("Не удалось загрузить файл для KIE")

    async def upload_stream(
        self,
        path: Path,
        *,
        upload_path: str = "telegram",
        file_name: str | None = None,
    ) -> str:
        name = file_name or path.name
        async with httpx.AsyncClient(timeout=120) as client:
            with path.open("rb") as handle:
                response = await client.post(
                    f"{self.base_url}/api/file-stream-upload",
                    headers=self.headers,
                    files={"file": (name, handle)},
                    data={"uploadPath": upload_path, "fileName": name},
                )
            response.raise_for_status()
            body = response.json()

        if not body.get("success") and body.get("code") not in {200, None}:
            raise ValueError(body.get("msg") or "KIE upload failed")

        data = body.get("data") or {}
        file_url = data.get("fileUrl") or data.get("downloadUrl")
        if not file_url:
            raise ValueError("KIE upload не вернул URL файла")
        return str(file_url)

    async def upload_from_url(
        self,
        file_url: str,
        *,
        upload_path: str = "telegram",
        file_name: str | None = None,
    ) -> str:
        payload: dict[str, str] = {"fileUrl": file_url, "uploadPath": upload_path}
        if file_name:
            payload["fileName"] = file_name

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self.base_url}/api/file-url-upload",
                headers={**self.headers, "Content-Type": "application/json"},
                json=payload,
            )
            response.raise_for_status()
            body = response.json()

        if not body.get("success") and body.get("code") not in {200, None}:
            raise ValueError(body.get("msg") or "KIE url-upload failed")

        data = body.get("data") or {}
        uploaded = data.get("fileUrl") or data.get("downloadUrl")
        if not uploaded:
            raise ValueError("KIE url-upload не вернул URL файла")
        return str(uploaded)
