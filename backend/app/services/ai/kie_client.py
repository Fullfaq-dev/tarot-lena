import json
from collections.abc import AsyncIterator

import httpx

from app.core.config import get_settings


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

    async def stream_chat(self, messages: list[dict], reasoning_effort: str = "low") -> AsyncIterator[str]:
        self.last_usage = None
        if self.settings.kie_api_key == "replace-me":
            yield self._local_fallback(messages)
            return

        url = f"{self.settings.kie_base_url.rstrip('/')}/gemini-3-flash/v1/chat/completions"
        payload = {
            "messages": messages,
            "stream": True,
            "include_thoughts": False,
            "reasoning_effort": reasoning_effort,
        }
        async with httpx.AsyncClient(timeout=90) as client:
            async with client.stream("POST", url, headers=self.headers, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line.removeprefix("data: ").strip()
                    if data == "[DONE]":
                        break
                    try:
                        event = json.loads(data)
                    except json.JSONDecodeError:
                        continue

                    usage = event.get("usage")
                    if usage:
                        self.last_usage = {
                            "input_tokens": int(
                                usage.get("prompt_tokens") or usage.get("input_tokens") or 0
                            ),
                            "output_tokens": int(
                                usage.get("completion_tokens") or usage.get("output_tokens") or 0
                            ),
                        }

                    choices = event.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta", {}).get("content")
                    if delta:
                        yield delta

    async def chat_completion(
        self,
        messages: list[dict],
        *,
        reasoning_effort: str = "low",
    ) -> str:
        self.last_usage = None
        if self.settings.kie_api_key == "replace-me":
            return self._local_fallback(messages)

        url = f"{self.settings.kie_base_url.rstrip('/')}/gemini-3-flash/v1/chat/completions"
        payload = {
            "messages": messages,
            "stream": False,
            "include_thoughts": False,
            "reasoning_effort": reasoning_effort,
        }
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            data = response.json()

        usage = data.get("usage") or {}
        self.last_usage = {
            "input_tokens": int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0),
            "output_tokens": int(usage.get("completion_tokens") or usage.get("output_tokens") or 0),
        }
        choices = data.get("choices") or []
        if not choices:
            return ""
        return choices[0].get("message", {}).get("content", "") or ""

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

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{self.settings.kie_base_url.rstrip('/')}/api/v1/jobs/recordInfo",
                headers=self.headers,
                params={"taskId": task_id},
            )
            response.raise_for_status()
            return response.json()

    async def create_media_task(self, model: str, input_payload: dict, callback_url: str | None = None) -> dict:
        if self.settings.kie_api_key == "replace-me":
            return {"code": 200, "msg": "local", "data": {"taskId": f"local_{model}"}}

        payload = {"model": model, "input": input_payload}
        if callback_url:
            payload["callBackUrl"] = callback_url
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.settings.kie_base_url.rstrip('/')}/api/v1/jobs/createTask",
                headers=self.headers,
                json=payload,
            )
            response.raise_for_status()
            body = response.json()

        code = int(body.get("code") or 200)
        if code != 200:
            raise ValueError(body.get("msg") or f"KIE createTask вернул код {code}")
        if not (body.get("data") or {}).get("taskId"):
            raise ValueError(body.get("msg") or "KIE не вернул taskId")
        return body

    def _local_fallback(self, messages: list[dict]) -> str:
        user_text = ""
        for message in reversed(messages):
            if message.get("role") == "user":
                content = message.get("content") or []
                if content and isinstance(content, list):
                    user_text = content[0].get("text", "")
                break
        return (
            "Я рядом. Пока KIE_API_KEY не настроен, отвечаю в локальном режиме. "
            f"Твой запрос: «{user_text}». В рабочем режиме я учту профиль, память, расклады и дам живой персональный ответ."
        )
