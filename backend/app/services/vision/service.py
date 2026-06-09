import asyncio
import json
import re
from collections.abc import Awaitable, Callable
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

_IMAGE_STYLE = (
    "Minimal luxury infographic on pure white background. "
    "Elegant thin golden serif typography for all Russian text labels. "
    "Generous whitespace, clean editorial layout, soft semi-illustrated style. "
    "Do NOT copy the reference photo 1:1. Transform and stylize the subject. "
    "No dark background, no horror uncanny realism, no photographic skin pores."
)

_JSON_SYSTEM = (
    "Ты анализируешь фото для эзотерического Telegram-бота.\n"
    "Ответь ТОЛЬКО JSON-объектом, без markdown-обёртки и без пояснений.\n"
    "interpretation — 2-4 предложения по-русски, markdown **жирный** *курсив*, без HTML.\n\n"
    'Для aura: {"interpretation":"...", "aura_color":"english color phrase", '
    '"aura_title":"короткий заголовок на русском", "image_summary":"1-2 предложения на русском для подписи на картинке"}\n'
    'Для palm: {"interpretation":"...", "palm_lines":[{"name":"Линия сердца","note":"кратко на русском"},'
    '{"name":"Линия ума","note":"..."},{"name":"Линия жизни","note":"..."},{"name":"Линия судьбы","note":"..."}], '
    '"image_summary":"краткая общая подпись на русском"}'
)

_ANALYSIS_PROMPTS = {
    "aura": (
        "Проанализируй фото как символическую ауру (развлекательная интерпретация, "
        "без медицинских утверждений). Определи цвет ауры, заголовок и краткое описание для инфографики."
    ),
    "palm": (
        "Проанализируй фото ладони (развлекательная хиромантия, без медицинских утверждений). "
        "Опиши линии сердца, ума, жизни и судьбы с краткими пояснениями на русском."
    ),
}

_DEFAULT_AURA = {
    "aura_color": "soft golden violet gradient",
    "aura_title": "Аура",
    "image_summary": "Символическое энергетическое поле",
}

_DEFAULT_PALM_LINES = [
    {"name": "Линия сердца", "note": "эмоции и отношения"},
    {"name": "Линия ума", "note": "мышление и решения"},
    {"name": "Линия жизни", "note": "энергия и жизненный путь"},
    {"name": "Линия судьбы", "note": "направление и предназначение"},
]


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
        on_analysis_complete: Callable[[str], Awaitable[None]] | None = None,
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
            if on_analysis_complete is not None:
                await on_analysis_complete(interpretation)
            infographic_urls = await self._generate_infographic(
                user_id=user.id,
                source_image_url=image_url,
                mode=mode,
                parsed=parsed,
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

    async def _analyze_structured(self, messages: list[dict], mode: str) -> dict:
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

    def _build_image_prompt(self, mode: str, parsed: dict) -> str:
        if mode == "aura":
            aura_color = parsed.get("aura_color") or _DEFAULT_AURA["aura_color"]
            aura_title = parsed.get("aura_title") or _DEFAULT_AURA["aura_title"]
            image_summary = parsed.get("image_summary") or _DEFAULT_AURA["image_summary"]
            return (
                f"{_IMAGE_STYLE} "
                "Create an aura reading card from the reference photo. "
                "Show a soft semi-illustrated human silhouette based on the person's pose in the reference — "
                "abstracted outline, not photorealistic, no detailed facial skin texture. "
                f"Surround the silhouette with a glowing aura in {aura_color} tones. "
                f'Place Russian golden text on white background: title "{aura_title}", '
                f'description "{image_summary}". '
                "Elegant minimal poster, white background only."
            )

        lines = parsed.get("palm_lines") or _DEFAULT_PALM_LINES
        if isinstance(lines, list):
            line_block = "; ".join(
                f'{item.get("name", "Линия")}: {item.get("note", "")}'
                for item in lines
                if isinstance(item, dict)
            )
        else:
            line_block = str(lines)

        image_summary = parsed.get("image_summary") or "Хиромантический разбор ладони"
        return (
            f"{_IMAGE_STYLE} "
            "Create a palmistry reading card from the reference hand photo. "
            "Keep a similar hand pose and proportions from the reference but render as a clean simplified "
            "semi-illustrated drawing — not a photographic 1:1 copy, no creepy realism. "
            "Overlay thin golden palmistry lines (heart, head, life, fate) with short Russian annotations: "
            f"{line_block}. "
            f'Add a short Russian golden caption: "{image_summary}". '
            "White background only, educational minimal layout."
        )

    async def _generate_infographic(
        self,
        *,
        user_id: str,
        source_image_url: str,
        mode: str,
        parsed: dict,
    ) -> list[str]:
        settings = get_settings()
        prompt = self._build_image_prompt(mode, parsed)
        payload = {
            "prompt": prompt,
            "input_urls": [source_image_url],
            "aspect_ratio": "4:5",
            "resolution": "1K",
            "nsfw_checker": False,
        }
        response = await self.kie.create_media_task(
            "gpt-image-2-image-to-image",
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

    def _coerce_structured_response(self, raw: str, mode: str) -> dict:
        parsed = self._parse_json_response(raw)
        interpretation = str(parsed.get("interpretation", "")).strip()

        if not interpretation:
            interpretation = self._extract_json_string_field(raw, "interpretation")
        if not interpretation:
            cleaned = re.sub(r"```(?:json)?|```", "", raw).strip()
            if cleaned and not cleaned.startswith("{"):
                interpretation = cleaned[:2000]

        if not interpretation:
            raise ValueError("Модель вернула неполный ответ")

        result: dict = {"interpretation": interpretation}

        if mode == "aura":
            result["aura_color"] = (
                str(parsed.get("aura_color", "")).strip() or _DEFAULT_AURA["aura_color"]
            )
            result["aura_title"] = (
                str(parsed.get("aura_title", "")).strip() or _DEFAULT_AURA["aura_title"]
            )
            result["image_summary"] = (
                str(parsed.get("image_summary", "")).strip() or _DEFAULT_AURA["image_summary"]
            )
            return result

        palm_lines = parsed.get("palm_lines")
        if isinstance(palm_lines, list) and palm_lines:
            result["palm_lines"] = [
                {
                    "name": str(item.get("name", "Линия")).strip(),
                    "note": str(item.get("note", "")).strip(),
                }
                for item in palm_lines
                if isinstance(item, dict)
            ]
        else:
            result["palm_lines"] = _DEFAULT_PALM_LINES

        result["image_summary"] = (
            str(parsed.get("image_summary", "")).strip() or "Хиромантический разбор ладони"
        )
        return result

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
