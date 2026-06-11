import logging
from pathlib import Path

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_OGG_ALIASES = {".oga", ".opus"}


def kie_friendly_filename(path: Path, *, kind: str = "file") -> str:
    suffix = path.suffix.lower()
    if kind == "audio" and suffix in _OGG_ALIASES:
        return f"{path.stem}.ogg"
    return path.name


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
        kind: str = "file",
    ) -> str:
        if self.settings.kie_api_key == "replace-me":
            if source_url:
                return source_url
            raise ValueError("KIE API key не настроен")

        errors: list[str] = []

        if local_path and local_path.exists():
            try:
                url = await self.upload_stream(
                    local_path,
                    upload_path=upload_path,
                    file_name=file_name or kie_friendly_filename(local_path, kind=kind),
                    kind=kind,
                )
                logger.info("KIE upload ok path=%s url=%s", local_path.name, url[:80])
                return url
            except Exception as exc:
                errors.append(f"stream: {exc}")
                logger.warning("KIE stream upload failed path=%s: %s", local_path, exc)

        if source_url:
            try:
                url = await self.upload_from_url(
                    source_url,
                    upload_path=upload_path,
                    file_name=file_name,
                )
                logger.info("KIE url-upload ok source=%s url=%s", source_url[:80], url[:80])
                return url
            except Exception as exc:
                errors.append(f"url: {exc}")
                logger.warning("KIE url upload failed url=%s: %s", source_url, exc)

        detail = "; ".join(errors) if errors else "нет локального файла и URL"
        raise ValueError(f"Не удалось загрузить файл в KIE ({detail})")

    async def upload_stream(
        self,
        path: Path,
        *,
        upload_path: str = "telegram",
        file_name: str | None = None,
        kind: str = "file",
    ) -> str:
        name = file_name or kie_friendly_filename(path, kind=kind)
        content = path.read_bytes()
        if not content:
            raise ValueError("Пустой файл")

        mime = "application/octet-stream"
        if kind == "audio":
            mime = "audio/ogg"
        elif kind == "image":
            suffix = path.suffix.lower()
            mime = "image/jpeg" if suffix in {".jpg", ".jpeg"} else "image/png"

        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{self.base_url}/api/file-stream-upload",
                headers=self.headers,
                files={"file": (name, content, mime)},
                data={"uploadPath": upload_path, "fileName": name},
            )
            response.raise_for_status()
            body = response.json()

        return self._extract_file_url(body)

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

        return self._extract_file_url(body)

    @staticmethod
    def _extract_file_url(body: dict) -> str:
        code = body.get("code")
        if code is not None and int(code) != 200:
            raise ValueError(body.get("msg") or f"KIE upload code {code}")
        if body.get("success") is False:
            raise ValueError(body.get("msg") or "KIE upload failed")

        data = body.get("data") or {}
        file_url = data.get("fileUrl") or data.get("downloadUrl")
        if not file_url:
            raise ValueError("KIE upload не вернул URL файла")
        return str(file_url)
