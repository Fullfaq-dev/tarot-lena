import asyncio
import json

from app.services.ai.kie_client import KieClient


def _parse_result_json(raw: str | dict) -> dict:
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}


def extract_urls_and_text(record: dict) -> tuple[list[str], str | None]:
    data = record.get("data") or {}
    state = str(data.get("state", "")).lower()

    if state == "fail":
        raise ValueError(data.get("failMsg") or "Задача KIE завершилась с ошибкой")

    if state != "success":
        return [], None

    parsed = _parse_result_json(data.get("resultJson") or "{}")
    urls = parsed.get("resultUrls") or parsed.get("audioUrl") or parsed.get("audio_url") or []
    if isinstance(urls, str):
        urls = [urls]

    text = (
        parsed.get("text")
        or parsed.get("transcript")
        or parsed.get("result")
        or data.get("text")
        or ""
    )
    if isinstance(text, dict):
        text = text.get("text") or text.get("transcript") or ""
    text = str(text).strip() or None
    return [str(url) for url in urls if url], text


async def wait_for_media_task(
    task_id: str,
    *,
    timeout_sec: int = 180,
    interval_sec: float = 2.0,
) -> tuple[list[str], str | None]:
    if task_id.startswith("local_"):
        return [], None

    kie = KieClient()
    deadline = asyncio.get_running_loop().time() + timeout_sec
    while asyncio.get_running_loop().time() < deadline:
        record = await kie.get_task_record(task_id)
        data = record.get("data") or {}
        state = str(data.get("state", "")).lower()

        if state in {"success", "fail"}:
            return extract_urls_and_text(record)

        await asyncio.sleep(interval_sec)

    raise TimeoutError("Превышено время ожидания задачи KIE")
