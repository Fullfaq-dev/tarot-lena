import asyncio
import json
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from aiogram import Bot
from aiogram.types import User as TelegramUser
from sqlalchemy import select

from app.core.config import get_settings
from app.bot.i18n import normalize_language, t
from app.bot.i18n_ai import vision_analysis_prompt, vision_image_base, vision_json_system
from app.database.models import Message, MessageRole, SoulProfile, User, UserSettings
from app.database.session import AsyncSessionLocal
from app.services.ai.context import ContextBuilder
from app.services.ai.kie_client import KieClient
from app.services.billing.service import BillingService
from app.services.media.service import MediaJobService
from app.services.media.telegram_photo import store_telegram_photo
from app.services.media.kie_upload import KieFileUpload

_VISION_MODE_LABEL_KEYS = {
    "aura": "spend_aura",
    "palm": "spend_palm",
    "custom": "spend_photo",
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
        self.kie_upload = KieFileUpload()

    @staticmethod
    async def _lang_for_user(session, user: User) -> str:
        settings = await session.scalar(select(UserSettings).where(UserSettings.user_id == user.id))
        return normalize_language(settings.ui_language if settings else "en")

    @staticmethod
    def _mode_label(mode: str, lang: str) -> str:
        key = _VISION_MODE_LABEL_KEYS.get(mode, "spend_photo")
        return t(key, lang)

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
        fallback_lang = normalize_language(
            telegram_user.language_code if telegram_user else "en"
        )
        if telegram_user is None:
            return None, t("error_telegram_profile", fallback_lang)

        with_infographic = mode in {"aura", "palm"}
        feature = f"vision_{mode}"

        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_user.id))
            if user is None:
                return None, t("error_need_start", fallback_lang)

            lang = await self._lang_for_user(session, user)

            stored = await store_telegram_photo(bot, file_id)
            image_url = await self.kie_upload.ensure_kie_url(
                local_path=stored.path,
                source_url=stored.public_url,
                upload_path="vision",
                file_name=stored.path.name,
                kind="image",
            )

            if mode == "custom":
                question = custom_text.strip() or t("vision_custom_default_question", lang)
                user_content = [
                    {
                        "type": "text",
                        "text": t("vision_custom_instruction", lang, question=question),
                    },
                    {"type": "image_url", "image_url": {"url": image_url}},
                ]
            else:
                question = t("vision_analysis_prefix", lang, label=self._mode_label(mode, lang))
                user_content = [
                    {"type": "text", "text": vision_analysis_prompt(lang, mode)},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ]

            messages = await self.context_builder.build(
                session, user, user_query=custom_text.strip() or question
            )
            if mode != "custom":
                self._append_json_instruction(messages, lang)
            messages.append({"role": "user", "content": user_content})

            allowed, reason, billing_mode = await self.billing.ensure_can_use_vision(
                session,
                user,
                with_infographic=with_infographic,
                vision_mode=mode if with_infographic else None,
                context_messages=messages,
            )
            if not allowed:
                return None, reason

            billing_mode = await self.billing.reserve_chat_slot(session, user, billing_mode)

            user_message = Message(
                user_id=user.id,
                role=MessageRole.USER.value,
                content=question,
                meta={
                    "vision_mode": mode,
                    "has_image": True,
                    "source_image_url": stored.public_url,
                    "kie_image_url": image_url,
                },
            )
            profile = await session.scalar(select(SoulProfile).where(SoulProfile.user_id == user.id))
            subject_gender = profile.gender if profile else None

            session.add(user_message)
            await session.flush()
            await session.commit()

        try:
            if mode == "custom":
                interpretation = await self._analyze_custom(messages, lang)
                usage = await self._finalize_usage(
                    user.id,
                    question,
                    interpretation,
                    feature=feature,
                    context_messages=messages,
                    billing_mode=billing_mode,
                    with_infographic=False,
                    source_image_url=stored.public_url,
                    vision_mode=mode,
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

            parsed = await self._analyze_structured(messages, mode, lang)
            interpretation = parsed["interpretation"]
            if on_analysis_complete is not None:
                await on_analysis_complete(interpretation)
            infographic_urls = await self._generate_infographic(
                user_id=user.id,
                source_image_url=image_url,
                mode=mode,
                parsed=parsed,
                subject_gender=subject_gender,
                lang=lang,
            )
            usage = await self._finalize_usage(
                user.id,
                question,
                interpretation,
                feature=feature,
                context_messages=messages,
                billing_mode=billing_mode,
                with_infographic=True,
                source_image_url=stored.public_url,
                infographic_urls=infographic_urls,
                vision_mode=mode,
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
            return None, t("error_photo_process", lang, detail=exc)

    async def _analyze_custom(self, messages: list[dict], lang: str) -> str:
        for effort in ("low", "medium"):
            answer = await self.kie.chat_completion(messages, reasoning_effort=effort)
            if answer.strip():
                return answer.strip()

        simplified: list[dict] = []
        if messages and messages[0].get("role") == "system":
            simplified.append(messages[0])
        for message in reversed(messages):
            if message.get("role") != "user":
                continue
            content = message.get("content")
            if isinstance(content, list) and any(
                part.get("type") == "image_url" for part in content if isinstance(part, dict)
            ):
                simplified.append(message)
                break

        if len(simplified) >= 2:
            answer = await self.kie.chat_completion(simplified, reasoning_effort="low")
            if answer.strip():
                return answer.strip()

        raise ValueError(t("vision_model_no_response", lang))

    async def _analyze_structured(self, messages: list[dict], mode: str, lang: str) -> dict:
        raw = await self.kie.chat_completion(messages, reasoning_effort="medium")
        try:
            return self._coerce_structured_response(raw, mode, lang)
        except ValueError:
            pass

        retry_messages = [
            *messages,
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": t("vision_json_retry", lang, mode=mode, raw=raw[:2000]),
                    }
                ],
            },
        ]
        raw_retry = await self.kie.chat_completion(retry_messages, reasoning_effort="medium")
        try:
            return self._coerce_structured_response(raw_retry, mode, lang)
        except ValueError:
            pass

        strict_messages = [
            {
                "role": "system",
                "content": [{"type": "text", "text": vision_json_system(lang)}],
            },
            *[
                m
                for m in messages
                if not (m.get("role") == "system" and isinstance(m.get("content"), list))
            ],
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": t("vision_json_strict", lang),
                    }
                ],
            },
        ]
        raw_strict = await self.kie.chat_completion(strict_messages, reasoning_effort="medium")
        try:
            return self._coerce_structured_response(raw_strict, mode, lang)
        except ValueError:
            return await self._fallback_plain_analysis(messages, mode, lang)

    async def _fallback_plain_analysis(self, messages: list[dict], mode: str, lang: str) -> dict:
        plain_messages: list[dict] = [
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": t("vision_fallback_system", lang),
                    }
                ],
            }
        ]
        for item in messages:
            if item.get("role") == "system":
                continue
            plain_messages.append(item)

        interpretation = await self.kie.chat_completion(plain_messages, reasoning_effort="medium")
        interpretation = interpretation.strip()
        if not interpretation:
            raise ValueError(t("vision_incomplete_response", lang))

        if mode == "aura":
            return {
                "interpretation": interpretation,
                **_DEFAULT_AURA,
            }
        return {
            "interpretation": interpretation,
            "palm_lines": _DEFAULT_PALM_LINES,
            "image_summary": t("vision_palm_summary_default", lang),
        }

    @staticmethod
    def _subject_gender_hint(gender: str | None) -> str:
        normalized = (gender or "").strip().lower()
        if normalized in {"мужской", "male", "м", "man"}:
            return (
                "The silhouette must be clearly masculine male: male body proportions, "
                "male facial outline, no feminine features, no dress, no makeup, no bun hairstyle."
            )
        if normalized in {"женский", "female", "ж", "woman"}:
            return (
                "The silhouette must be clearly feminine female: female body proportions "
                "and feminine outline."
            )
        return "Use a neutral androgynous adult silhouette without strong gender markers."

    def _build_image_prompt(
        self, mode: str, parsed: dict, *, subject_gender: str | None = None, lang: str = "ru"
    ) -> str:
        image_base = vision_image_base(lang)
        gender_hint = self._subject_gender_hint(subject_gender)
        if mode == "aura":
            aura_color = parsed.get("aura_color") or _DEFAULT_AURA["aura_color"]
            aura_title = parsed.get("aura_title") or _DEFAULT_AURA["aura_title"]
            image_summary = parsed.get("image_summary") or _DEFAULT_AURA["image_summary"]
            return (
                f"{image_base} "
                "Create a clean, minimal, high-end esoteric aura reading report based on this photo. "
                "Black-on-white design with thin lines, rounded cards, and a luxury aesthetic. "
                "Include a simple contour line drawing of the person's silhouette from the reference — "
                "not photorealistic, no detailed skin texture. "
                f"{gender_hint} "
                "Focus on mystical aura reading only (energy field, aura colors, spiritual tone, inner strengths, "
                "areas for inner growth, symbolic recommendations) — NOT beauty ratings, NOT attractiveness scores, "
                "NOT medical claims. "
                f"Show a soft glowing aura in {aura_color} tones around the contour. "
                f'Russian text on the card: title "{aura_title}", summary "{image_summary}". '
                "Visually refined, honest symbolic esoteric tone, small piece of art."
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

        image_summary = parsed.get("image_summary") or t("vision_palm_summary_default", lang)
        return (
            f"{image_base} "
            "Based on the reference hand photo, create a complete esoteric palm reading guide. "
            "Analyze the palm in a clean minimalistic style: thin lines, rounded map cards, very attractive layout. "
            "Focus on palmistry reading. Create a simple black and white outline of the main lines "
            "(heart, head, life, fate) like a small piece of art. "
            "Keep similar hand pose and proportions from the reference but stylized — "
            "not a photographic 1:1 copy. "
            f"Russian annotations for each line: {line_block}. "
            f'Russian caption: "{image_summary}". '
            "Entertainment-only esoteric palmistry, refined and elegant."
        )

    async def _generate_infographic(
        self,
        *,
        user_id: str,
        source_image_url: str,
        mode: str,
        parsed: dict,
        subject_gender: str | None = None,
        lang: str = "ru",
    ) -> list[str]:
        settings = get_settings()
        prompt = self._build_image_prompt(mode, parsed, subject_gender=subject_gender, lang=lang)
        payload = {
            "prompt": prompt,
            "input_urls": [source_image_url],
            "aspect_ratio": "4:5",
            "resolution": "1K",
            "nsfw_checker": False,
        }
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                response = await self.kie.create_media_task(
                    "gpt-image-2-image-to-image",
                    payload,
                    callback_url=f"{settings.public_base_url.rstrip('/')}/callbacks/kie",
                )
                task_id = KieClient.task_id_from_response(response)
                if not task_id:
                    raise ValueError(t("vision_task_create_failed", lang))

                await self.jobs.create_job(
                    f"{mode}_infographic",
                    {**payload, "provider_task_id": task_id},
                    user_id=user_id,
                )
                return await self._wait_for_result_urls(task_id, lang=lang)
            except Exception as exc:
                last_error = exc
                if attempt == 0:
                    await asyncio.sleep(2.0)
        raise last_error or ValueError(t("vision_generation_failed", lang))

    async def _wait_for_result_urls(
        self,
        task_id: str,
        *,
        timeout_sec: int = 300,
        interval_sec: float = 2.0,
        lang: str = "ru",
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
                raise ValueError(t("vision_no_image_url", lang))

            if state == "fail":
                raise ValueError(data.get("failMsg") or t("vision_generation_failed", lang))

            await asyncio.sleep(interval_sec)

        raise TimeoutError(t("vision_generation_timeout", lang))

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
        source_image_url: str | None = None,
        infographic_urls: list[str] | None = None,
        vision_mode: str | None = None,
    ) -> dict:
        async with AsyncSessionLocal() as session:
            user = await session.scalar(select(User).where(User.id == user_id))
            if user is None:
                return {"charged_rub": "0", "billing_mode": billing_mode, "balance_after": 0}

            extra_meta: dict = {}
            if source_image_url:
                extra_meta["source_image_url"] = source_image_url
            if infographic_urls:
                extra_meta["infographic_urls"] = infographic_urls
            if vision_mode:
                extra_meta["vision_mode"] = vision_mode

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
                vision_mode=vision_mode if with_infographic else None,
                extra_meta=extra_meta or None,
            )

            assistant_meta = {
                "feature": feature,
                "billing_mode": billing_mode,
                "provider_cost_usd": str(usage.get("provider_cost_usd", 0)),
                "charged_rub": str(usage.get("charged_rub", 0)),
                **extra_meta,
            }
            if with_infographic:
                assistant_meta["with_infographic"] = True

            session.add(
                Message(
                    user_id=user.id,
                    role=MessageRole.ASSISTANT.value,
                    content=answer,
                    tokens_input=int(usage.get("input_tokens") or 0),
                    tokens_output=int(usage.get("output_tokens") or 0),
                    cost_rub=usage.get("charged_rub") or 0,
                    meta=assistant_meta,
                )
            )
            await session.commit()
            return usage

    @staticmethod
    def _append_json_instruction(messages: list[dict], lang: str) -> None:
        json_system = vision_json_system(lang)
        if not messages or messages[0].get("role") != "system":
            messages.insert(0, {"role": "system", "content": [{"type": "text", "text": json_system}]})
            return
        content = messages[0].get("content")
        if isinstance(content, list) and content and isinstance(content[0], dict):
            content[0]["text"] = f"{content[0].get('text', '')}\n\n{json_system}"
        elif isinstance(content, str):
            messages[0]["content"] = f"{content}\n\n{json_system}"

    def _coerce_structured_response(self, raw: str, mode: str, lang: str) -> dict:
        parsed = self._parse_json_response(raw)
        interpretation = str(parsed.get("interpretation", "")).strip()

        if not interpretation:
            interpretation = self._extract_json_string_field(raw, "interpretation")
        if not interpretation:
            cleaned = re.sub(r"```(?:json)?|```", "", raw).strip()
            if cleaned and not cleaned.startswith("{"):
                interpretation = cleaned[:2000]

        if not interpretation:
            raise ValueError(t("vision_incomplete_response", lang))

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
            str(parsed.get("image_summary", "")).strip() or t("vision_palm_summary_default", lang)
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
