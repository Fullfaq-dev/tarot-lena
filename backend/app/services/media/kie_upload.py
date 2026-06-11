import asyncio
import base64
import logging
from collections.abc import Awaitable, Callable
from pathlib import Path

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_OGG_ALIASES = {".oga", ".opus"}
_RETRYABLE_MARKERS = (
    "server exception",
    "try again",
    "timeout",
    "temporarily",
    "503",
    "502",
    "500",
)


def kie_friendly_filename(path: Path, *, kind: str = "file") -> str:
    suffix = path.suffix.lower()
    if kind == "audio" and suffix in _OGG_ALIASES:
        return f"{path.stem}.ogg"
    return path.name


def _is_retryable_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return any(marker in message for marker in _RETRYABLE_MARKERS)


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
        name = file_name
        if local_path and local_path.exists() and not name:
            name = kie_friendly_filename(local_path, kind=kind)

        strategies: list[tuple[str, Callable[[], Awaitable[str]]]] = []
        if local_path and local_path.exists() and kind == "audio" and local_path.stat().st_size <= 10 * 1024 * 1024:
            strategies.append(
                (
                    "base64",
                    lambda: self.upload_base64(local_path, upload_path=upload_path, file_name=name, kind=kind),
                )
            )
        if source_url:
            strategies.append(
                (
                    "url",
                    lambda: self.upload_from_url(source_url, upload_path=upload_path, file_name=name),
                )
            )
        if local_path and local_path.exists():
            strategies.append(
                (
                    "stream",
                    lambda: self.upload_stream(
                        local_path,
                        upload_path=upload_path,
                        file_name=name or local_path.name,
                        kind=kind,
                    ),
                )
            )

        for label, action in strategies:
            try:
                url = await self._with_retries(action, label=label)
                logger.info("KIE upload ok via %s url=%s", label, url[:100])
                return url
            except Exception as exc:
                errors.append(f"{label}: {exc}")
                logger.warning("KIE %s upload failed: %s", label, exc)

        detail = "; ".join(errors) if errors else "нет локального файла и URL"
        raise ValueError(f"Не удалось загрузить файл в KIE ({detail})")

    async def _with_retries(self, action, *, label: str, attempts: int = 3) -> str:
        last_error: Exception | None = None
        for attempt in range(attempts):
            try:
                return await action()
            except Exception as exc:
                last_error = exc
                if attempt >= attempts - 1 or not _is_retryable_error(exc):
                    raise
                delay = 1.5 * (attempt + 1)
                logger.warning("KIE %s upload retry %s/%s after %ss: %s", label, attempt + 1, attempts, delay, exc)
                await asyncio.sleep(delay)
        raise last_error or RuntimeError("upload failed")

    async def upload_base64(
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

        payload = {
            "base64Data": f"data:{mime};base64,{base64.b64encode(content).decode('ascii')}",
            "uploadPath": upload_path,
            "fileName": name,
        }
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{self.base_url}/api/file-base64-upload",
                headers={**self.headers, "Content-Type": "application/json"},
                json=payload,
            )
            response.raise_for_status()
            body = response.json()
        return self._extract_file_url(body)

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

        async with httpx.AsyncClient(timeout=90) as client:
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
