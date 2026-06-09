import asyncio
import json
import re
from dataclasses import dataclass

from aiogram import Bot
from aiogram.types import User as TelegramUser
from sqlalchemy import select

from app.core.config import get_settings
from app.database.models import Message, MessageRole, User
from app.database.session import AsyncSessionLocal
from app.services.ai.context import ContextBuilder
from app.services.ai.kie_client import KieClient
from app.services.billing.service import BillingService
from app.services.media.service import MediaJobService
from app.services.media.telegram_photo import store_telegram_photo

_MODE_LABELS = {
    "aura": "Аура",
    "palm": "Ладонь",
    "custom": "Фото",
}

_JSON_SYSTEM = (
    "Ты анализируешь фото для эзотерического Telegram-бота.\n"
    "Ответь ТОЛЬКО JSON-объектом, без markdown-обёртки и без пояснений.\n"
    'Формат: {"interpretation":"...", "image_prompt":"..."}\n'
    "interpretation — 2-4 предложения по-русски, markdown **жирный** *курсив*, без HTML.\n"
    "image_prompt — подробный промпт на английском для полностью нарисованной инфографики "
    "(не фото, не фотореализм)."
)

_ANALYSIS_PROMPTS = {
    "aura": (
        "Проанализируй фото как символическую ауру (развлекательная интерпретация, "
        "без медицинских утверждений). image_prompt: illustrated mystical Russian aura infographic, "
        "readable Russian labels, tarot aesthetics."
    ),
    "palm": (
        "Проанализируй фото ладони (развлекательная хиромантия, без медицинских утверждений). "
        "image_prompt: illustrated mystical Russian palmistry infographic with glowing line map, "
        "readable Russian labels, dark celestial background, tarot aesthetics."
    ),
}

_DEFAULT_IMAGE_PROMPTS = {
    "aura": (
        "Fully illustrated mystical Russian aura reading infographic, stylized symbolic human figure "
        "with soft gradient aura colors, readable Russian labels, ornate gold frame, dark celestial "
        "background, tarot aesthetics, no photograph, no photorealism"
    ),
    "palm": (
        "Fully illustrated mystical Russian palmistry infographic, stylized open palm with glowing "
        "golden line map, readable Russian labels for heart head life fate lines, ornate esoteric "
        "frame, dark celestial background, tarot aesthetics, no photograph, no photorealism"
    ),
}


@dataclass
class VisionResult:
    interpretation: str
    infographic_urls: list[str]
    billing_mode: str
    usage: dict
    feature: str


class VisionService:
    def __init__(self) -> None:
        self.kie = KieClient()
        self.jobs = MediaJobService()
        self.billing = BillingService()
        self.context_builder = ContextBuilder()

    async def process_photo(
        self,
        bot: Bot,
        telegram_user: TelegramUser,
        *,
        file_id: str,
        mode: str,
        custom_text: str = "",
    ) -> tuple[VisionResult | None, str | None]:
        if telegram_user is None:
            return None, "Не получилось определить профиль Telegram."

        with_infographic = mode in {"aura", "palm"}
        feature = f"vision_{mode}"

        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_user.id))
            if user is None:
                return None, "Сначала нажми /start, чтобы я создала твой профиль."

            messages = await self.context_builder.build(session, user)
            image_url = await store_telegram_photo(bot, file_id)

            if mode == "custom":
                question = custom_text.strip() or "Что ты видишь на этом фото?"
                user_content = [
                    {"type": "text", "text": question},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ]
            else:
                question = f"Анализ: {_MODE_LABELS[mode]}"
                self._append_json_instruction(messages)
                user_content = [
                    {"type": "text", "text": _ANALYSIS_PROMPTS[mode]},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ]

            messages.append({"role": "user", "content": user_content})

            allowed, reason, billing_mode = await self.billing.ensure_can_use_vision(
                session,
                user,
                with_infographic=with_infographic,
                context_messages=messages,
            )
            if not allowed:
                return None, reason

            billing_mode = await self.billing.reserve_chat_slot(session, user, billing_mode)

            user_message = Message(
                user_id=user.id,
                role=MessageRole.USER.value,
                content=question,
                meta={"vision_mode": mode, "has_image": True},
            )
            session.add(user_message)
            await session.flush()
            await session.commit()

        try:
            if mode == "custom":
                interpretation = await self._analyze_custom(messages)
                usage = await self._finalize_usage(
                    user.id,
                    question,
                    interpretation,
                    feature=feature,
                    context_messages=messages,
                    billing_mode=billing_mode,
                    with_infographic=False,
                )
                return (
                    VisionResult(
                        interpretation=interpretation,
                        infographic_urls=[],
                        billing_mode=billing_mode,
                        usage=usage,
                        feature=feature,
                    ),
                    None,
                )

            parsed = await self._analyze_structured(messages, mode)
            interpretation = parsed["interpretation"]
            infographic_urls = await self._generate_infographic(
                user_id=user.id,
                image_prompt=parsed["image_prompt"],
                mode=mode,
            )
            usage = await self._finalize_usage(
                user.id,
                question,
                interpretation,
                feature=feature,
                context_messages=messages,
                billing_mode=billing_mode,
                with_infographic=True,
            )
            return (
                VisionResult(
                    interpretation=interpretation,
                    infographic_urls=infographic_urls,
                    billing_mode=billing_mode,
                    usage=usage,
                    feature=feature,
                ),
                None,
            )
        except Exception as exc:
            return None, f"Не удалось обработать фото: {exc}"

    async def _analyze_custom(self, messages: list[dict]) -> str:
        answer = await self.kie.chat_completion(messages)
        return answer.strip() or "Не удалось получить ответ по фото."

    async def _analyze_structured(self, messages: list[dict], mode: str) -> dict[str, str]:
        raw = await self.kie.chat_completion(messages)
        try:
            return self._coerce_structured_response(raw, mode)
        except ValueError:
            retry_messages = [
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                f"{_JSON_SYSTEM}\n"
                                "Повтори ответ строго как JSON. Никакого текста вне JSON."
                            ),
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                f"Предыдущий ответ не удалось разобрать. Верни только JSON для режима {mode}.\n"
                                f"Предыдущий ответ:\n{raw[:3000]}"
                            ),
                        }
                    ],
                },
            ]
            raw_retry = await self.kie.chat_completion(retry_messages)
            return self._coerce_structured_response(raw_retry, mode)

    async def _generate_infographic(
        self,
        *,
        user_id: str,
        image_prompt: str,
        mode: str,
    ) -> list[str]:
        settings = get_settings()
        full_prompt = (
            f"{image_prompt.strip()} "
            "Fully illustrated esoteric infographic only. "
            "No real photograph, no photorealistic skin, no user photo reference. "
            "Stylized symbolic art with readable Russian text labels."
        )
        payload = {
            "prompt": full_prompt,
            "aspect_ratio": "4:5",
            "resolution": "1K",
            "nsfw_checker": False,
        }
        response = await self.kie.create_media_task(
            "gpt-image-2-text-to-image",
            payload,
            callback_url=f"{settings.public_base_url.rstrip('/')}/callbacks/kie",
        )
        task_id = response.get("data", {}).get("taskId")
        if not task_id:
            raise ValueError("Не удалось создать задачу генерации")

        await self.jobs.create_job(
            f"{mode}_infographic",
            {**payload, "provider_task_id": task_id},
            user_id=user_id,
        )
        return await self._wait_for_result_urls(task_id)

    async def _wait_for_result_urls(
        self,
        task_id: str,
        *,
        timeout_sec: int = 300,
        interval_sec: float = 3.0,
    ) -> list[str]:
        if task_id.startswith("local_"):
            return []

        deadline = asyncio.get_running_loop().time() + timeout_sec
        while asyncio.get_running_loop().time() < deadline:
            record = await self.kie.get_task_record(task_id)
            data = record.get("data") or {}
            state = str(data.get("state", "")).lower()

            if state == "success":
                result_json = data.get("resultJson") or "{}"
                if isinstance(result_json, str):
                    parsed = json.loads(result_json)
                else:
                    parsed = result_json
                urls = parsed.get("resultUrls") or []
                if urls:
                    return [str(url) for url in urls]
                raise ValueError("Генератор не вернул ссылку на изображение")

            if state == "fail":
                raise ValueError(data.get("failMsg") or "Генерация инфографики не удалась")

            await asyncio.sleep(interval_sec)

        raise TimeoutError("Превышено время ожидания инфографики")

    async def _finalize_usage(
        self,
        user_id: str,
        question: str,
        answer: str,
        *,
        feature: str,
        context_messages: list[dict],
        billing_mode: str,
        with_infographic: bool,
    ) -> dict:
        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.id == user_id))
            if user is None:
                return {"charged_rub": "0", "billing_mode": billing_mode, "balance_after": 0}

            usage = await self.billing.record_vision_usage(
                session,
                user,
                question,
                answer,
                feature=feature,
                context_messages=context_messages,
                api_usage=self.kie.last_usage,
                billing_mode=billing_mode,
                with_infographic=with_infographic,
            )
            await session.commit()
            return usage

    @staticmethod
    def _append_json_instruction(messages: list[dict]) -> None:
        if not messages or messages[0].get("role") != "system":
            messages.insert(0, {"role": "system", "content": [{"type": "text", "text": _JSON_SYSTEM}]})
            return
        content = messages[0].get("content")
        if isinstance(content, list) and content and isinstance(content[0], dict):
            content[0]["text"] = f"{content[0].get('text', '')}\n\n{_JSON_SYSTEM}"
        elif isinstance(content, str):
            messages[0]["content"] = f"{content}\n\n{_JSON_SYSTEM}"

    def _coerce_structured_response(self, raw: str, mode: str) -> dict[str, str]:
        parsed = self._parse_json_response(raw)
        interpretation = str(parsed.get("interpretation", "")).strip()
        image_prompt = str(parsed.get("image_prompt", "")).strip()

        if not interpretation:
            interpretation = self._extract_json_string_field(raw, "interpretation")
        if not image_prompt:
            image_prompt = self._extract_json_string_field(raw, "image_prompt")

        if not interpretation:
            cleaned = re.sub(r"```(?:json)?|```", "", raw).strip()
            if cleaned and not cleaned.startswith("{"):
                interpretation = cleaned[:2000]

        if not image_prompt:
            image_prompt = _DEFAULT_IMAGE_PROMPTS.get(mode, _DEFAULT_IMAGE_PROMPTS["palm"])

        if not interpretation:
            raise ValueError("Модель вернула неполный ответ")

        return {"interpretation": interpretation, "image_prompt": image_prompt}

    @staticmethod
    def _extract_json_string_field(raw: str, field: str) -> str:
        pattern = rf'"{field}"\s*:\s*"((?:\\.|[^"\\])*)"'
        match = re.search(pattern, raw, flags=re.DOTALL)
        if not match:
            return ""
        try:
            return json.loads(f'"{match.group(1)}"')
        except json.JSONDecodeError:
            return match.group(1).replace('\\"', '"').strip()

    @staticmethod
    def _parse_json_response(raw: str) -> dict:
        text = raw.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
            text = re.sub(r"\s*```$", "", text)

        candidates = [text]
        for match in re.finditer(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text, flags=re.DOTALL):
            candidates.append(match.group(0))

        for candidate in candidates:
            for payload in (candidate, candidate.replace("'", '"')):
                try:
                    parsed = json.loads(payload)
                    if isinstance(parsed, dict):
                        return parsed
                except json.JSONDecodeError:
                    continue

        return {}
