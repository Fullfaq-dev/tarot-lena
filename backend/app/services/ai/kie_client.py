import json
import logging
from collections.abc import AsyncIterator

import asyncio

from app.core.config import get_settings
from app.core.http import get_async_client

logger = logging.getLogger(__name__)


def _uses_responses_api(model: str) -> bool:
    """GPT-5.6 Luna/Sol/Terra живут на /codex/v1/responses, не на chat/completions."""
    normalized = (model or "").strip().lower().replace(".", "-")
    return normalized.startswith("gpt-5-6") or normalized.endswith("-luna")


def _map_reasoning_effort(effort: str, *, model: str = "") -> str:
    if _uses_responses_api(model):
        if effort in {"low", "medium", "high", "xhigh"}:
            return effort
        return "low"
    # GPT-5.2 chat/completions: only low/high
    if effort == "medium":
        return "high"
    if effort in {"low", "high"}:
        return effort
    return "low"


def _messages_to_responses_input(messages: list[dict]) -> tuple[str, list[dict]]:
    """Convert OpenAI-style messages to KIE Responses `instructions` + `input`."""
    instructions: list[str] = []
    items: list[dict] = []
    for message in messages:
        role = str(message.get("role") or "user")
        content = message.get("content")
        texts: list[str] = []
        parts: list[dict] = []
        if isinstance(content, str):
            texts.append(content)
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, str):
                    texts.append(part)
                    continue
                if not isinstance(part, dict):
                    continue
                if part.get("type") == "image_url":
                    image = part.get("image_url")
                    url = image.get("url") if isinstance(image, dict) else image
                    if url:
                        parts.append({"type": "input_image", "image_url": str(url)})
                elif part.get("text"):
                    texts.append(str(part["text"]))
        if role == "system":
            instructions.extend(t.strip() for t in texts if t and t.strip())
            continue
        for text in texts:
            if text.strip():
                parts.append({"type": "input_text", "text": text})
        if parts:
            items.append({"role": role if role in {"user", "assistant"} else "user", "content": parts})
    return "\n\n".join(instructions), items


def _extract_responses_text(data: dict) -> str:
    if isinstance(data.get("output_text"), str) and data["output_text"].strip():
        return data["output_text"].strip()
    parts: list[str] = []
    for item in data.get("output") or []:
        if not isinstance(item, dict):
            continue
        if item.get("type") not in {None, "message"} and item.get("role") != "assistant":
            continue
        for chunk in item.get("content") or []:
            if isinstance(chunk, dict) and chunk.get("text"):
                parts.append(str(chunk["text"]))
            elif isinstance(chunk, str):
                parts.append(chunk)
    return "\n".join(parts).strip()


def _normalize_messages(messages: list[dict]) -> list[dict]:
    """Flatten text-only arrays; keep multimodal parts with image_url intact."""
    out: list[dict] = []
    for message in messages:
        content = message.get("content")
        if not isinstance(content, list):
            out.append(message)
            continue

        has_image = any(
            isinstance(part, dict) and part.get("type") == "image_url" for part in content
        )
        if has_image:
            parts: list[dict] = []
            for part in content:
                if not isinstance(part, dict):
                    continue
                ptype = part.get("type")
                if ptype == "text":
                    text = str(part.get("text") or "").strip()
                    if text:
                        parts.append({"type": "text", "text": text})
                elif ptype == "image_url":
                    image = part.get("image_url")
                    url = image.get("url") if isinstance(image, dict) else None
                    if url:
                        parts.append({"type": "image_url", "image_url": {"url": str(url)}})
            out.append({**message, "content": parts})
            continue

        text_parts = []
        for part in content:
            if isinstance(part, dict) and part.get("text"):
                text_parts.append(str(part["text"]))
            elif isinstance(part, str):
                text_parts.append(part)
        out.append({**message, "content": "\n".join(text_parts)})
    return out


def _extract_content(data: dict) -> str:
    choices = data.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict) and part.get("text"):
                parts.append(str(part["text"]))
            elif isinstance(part, str):
                parts.append(part)
        return "\n".join(parts).strip()
    return (content or "").strip() if isinstance(content, str) else ""


class KieClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.last_usage: dict[str, int] | None = None

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.settings.kie_api_key}",
            "Content-Type": "application/json",
        }

    def _chat_url(self, model: str | None = None) -> str:
        chosen = (model or self.settings.kie_chat_model).strip("/")
        if _uses_responses_api(chosen):
            return f"{self.settings.kie_base_url.rstrip('/')}/codex/v1/responses"
        return f"{self.settings.kie_base_url.rstrip('/')}/{chosen}/v1/chat/completions"

    def _chat_models(self) -> list[str]:
        primary = (self.settings.kie_chat_model or "gpt-5-6-luna").strip()
        fallback = (getattr(self.settings, "kie_chat_fallback_model", "") or "").strip()
        models = [primary]
        if fallback and fallback != primary:
            models.append(fallback)
        return models

    async def stream_chat(self, messages: list[dict], reasoning_effort: str = "low") -> AsyncIterator[str]:
        self.last_usage = None
        if self.settings.kie_api_key == "replace-me":
            yield self._local_fallback(messages)
            return

        text = await self.chat_completion(messages, reasoning_effort=reasoning_effort)
        if text:
            yield text

    async def _chat_once(
        self,
        model: str,
        messages: list[dict],
        *,
        reasoning_effort: str,
    ) -> str:
        if _uses_responses_api(model):
            instructions, input_items = _messages_to_responses_input(_normalize_messages(messages))
            if not input_items:
                input_items = [{"role": "user", "content": [{"type": "input_text", "text": "Продолжи."}]}]
            payload = {
                "model": model,
                "stream": False,
                "input": input_items,
                "reasoning": {"effort": _map_reasoning_effort(reasoning_effort, model=model)},
            }
            if instructions:
                payload["instructions"] = instructions
        else:
            payload = {
                "messages": _normalize_messages(messages),
                "stream": False,
                "reasoning_effort": _map_reasoning_effort(reasoning_effort, model=model),
            }
        client = get_async_client()
        response = await client.post(
            self._chat_url(model),
            headers=self.headers,
            json=payload,
            timeout=75,
        )
        response.raise_for_status()
        data = response.json()

        code = data.get("code")
        if isinstance(code, int) and code not in (0, 200):
            raise ValueError(data.get("msg") or f"KIE chat code {code}")
        if isinstance(data.get("error"), dict):
            err = data["error"]
            raise ValueError(err.get("message") or str(err))

        usage = data.get("usage") or {}
        self.last_usage = {
            "input_tokens": int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0),
            "output_tokens": int(usage.get("completion_tokens") or usage.get("output_tokens") or 0),
        }
        text = _extract_responses_text(data) if _uses_responses_api(model) else _extract_content(data)
        if not text:
            raise ValueError(data.get("msg") or "KIE вернул пустой ответ")
        return text

    async def chat_completion(
        self,
        messages: list[dict],
        *,
        reasoning_effort: str = "low",
    ) -> str:
        self.last_usage = None
        if self.settings.kie_api_key == "replace-me":
            return self._local_fallback(messages)

        last_error: Exception | None = None
        for model in self._chat_models():
            for attempt in range(2):
                try:
                    text = await self._chat_once(
                        model, messages, reasoning_effort=reasoning_effort
                    )
                    if model != self.settings.kie_chat_model:
                        logger.warning("KIE fallback model used: %s", model)
                    return text
                except Exception as exc:
                    last_error = exc
                    msg = str(exc).lower()
                    retryable = any(
                        x in msg
                        for x in (
                            "server exception",
                            "try again",
                            "timeout",
                            "503",
                            "502",
                            "пусто",
                            "empty",
                        )
                    )
                    logger.warning(
                        "KIE chat failed model=%s attempt=%s: %s",
                        model,
                        attempt + 1,
                        exc,
                    )
                    if attempt == 0 and retryable:
                        await asyncio.sleep(1.0)
                        continue
                    break
        if last_error:
            raise last_error
        return ""

    async def get_task_record(self, task_id: str) -> dict:
        if self.settings.kie_api_key == "replace-me":
            return {
                "code": 200,
                "data": {
                    "taskId": task_id,
                    "state": "success",
                    "resultJson": json.dumps({"resultUrls": []}),
                },
            }

        client = get_async_client()
        response = await client.get(
            f"{self.settings.kie_base_url.rstrip('/')}/api/v1/jobs/recordInfo",
            headers=self.headers,
            params={"taskId": task_id},
            timeout=30,
        )
        response.raise_for_status()
        body = response.json()

        code = int(body.get("code") or 200)
        if body.get("data") is None:
            if code in {422, 404}:
                return {"code": code, "data": {"state": "waiting", "taskId": task_id}}
            raise ValueError(body.get("msg") or f"KIE recordInfo без data (code {code})")
        if code != 200:
            raise ValueError(body.get("msg") or f"KIE recordInfo code {code}")
        return body

    @staticmethod
    def task_id_from_response(response: dict) -> str | None:
        return (response.get("data") or {}).get("taskId")

    async def create_media_task(self, model: str, input_payload: dict, callback_url: str | None = None) -> dict:
        if self.settings.kie_api_key == "replace-me":
            return {"code": 200, "msg": "local", "data": {"taskId": f"local_{model}"}}

        payload = {"model": model, "input": input_payload}
        if callback_url:
            payload["callBackUrl"] = callback_url

        last_error: Exception | None = None
        for attempt in range(3):
            try:
                client = get_async_client()
                response = await client.post(
                    f"{self.settings.kie_base_url.rstrip('/')}/api/v1/jobs/createTask",
                    headers=self.headers,
                    json=payload,
                    timeout=45,
                )
                response.raise_for_status()
                body = response.json()

                code = int(body.get("code") or 200)
                if code != 200:
                    msg = body.get("msg") or f"KIE createTask вернул код {code}"
                    raise ValueError(msg)
                if not (body.get("data") or {}).get("taskId"):
                    raise ValueError(body.get("msg") or "KIE не вернул taskId")
                return body
            except Exception as exc:
                last_error = exc
                msg = str(exc).lower()
                retryable = any(x in msg for x in ("server exception", "try again", "timeout", "503", "502"))
                if attempt >= 2 or not retryable:
                    raise
                await asyncio.sleep(1.5 * (attempt + 1))
        raise last_error or RuntimeError("createTask failed")

    def _local_fallback(self, messages: list[dict]) -> str:
        user_text = ""
        for message in reversed(messages):
            if message.get("role") == "user":
                content = message.get("content") or []
                if content and isinstance(content, list):
                    user_text = content[0].get("text", "")
                elif isinstance(content, str):
                    user_text = content
                break
        return (
            "Я рядом. Пока KIE_API_KEY не настроен, отвечаю в локальном режиме. "
            f"Твой запрос: «{user_text}». В рабочем режиме я учту профиль, память, расклады и дам живой персональный ответ."
        )
