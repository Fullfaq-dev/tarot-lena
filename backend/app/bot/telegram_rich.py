"""Telegram Bot API rich message methods (not yet in aiogram)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from aiogram.methods.base import TelegramMethod
from aiogram.types import ChatIdUnion, Message, ReplyMarkupUnion, ReplyParameters
from aiogram.types.base import TelegramObject

if TYPE_CHECKING:
    from aiogram.client.bot import Bot


class InputRichMessage(TelegramObject):
    html: Optional[str] = None
    markdown: Optional[str] = None
    is_rtl: Optional[bool] = None
    skip_entity_detection: Optional[bool] = None


class SendRichMessage(TelegramMethod[Message]):
    __returning__ = Message
    __api_method__ = "sendRichMessage"

    chat_id: ChatIdUnion
    rich_message: InputRichMessage
    business_connection_id: Optional[str] = None
    message_thread_id: Optional[int] = None
    direct_messages_topic_id: Optional[int] = None
    disable_notification: Optional[bool] = None
    protect_content: Optional[bool] = None
    allow_paid_broadcast: Optional[bool] = None
    message_effect_id: Optional[str] = None
    reply_parameters: Optional[ReplyParameters] = None
    reply_markup: Optional[ReplyMarkupUnion] = None

    if TYPE_CHECKING:

        def __init__(
            __pydantic__self__,
            *,
            chat_id: ChatIdUnion,
            rich_message: InputRichMessage,
            business_connection_id: Optional[str] = None,
            message_thread_id: Optional[int] = None,
            direct_messages_topic_id: Optional[int] = None,
            disable_notification: Optional[bool] = None,
            protect_content: Optional[bool] = None,
            allow_paid_broadcast: Optional[bool] = None,
            message_effect_id: Optional[str] = None,
            reply_parameters: Optional[ReplyParameters] = None,
            reply_markup: Optional[ReplyMarkupUnion] = None,
            **__pydantic_kwargs: Any,
        ) -> None:
            super().__init__(
                chat_id=chat_id,
                rich_message=rich_message,
                business_connection_id=business_connection_id,
                message_thread_id=message_thread_id,
                direct_messages_topic_id=direct_messages_topic_id,
                disable_notification=disable_notification,
                protect_content=protect_content,
                allow_paid_broadcast=allow_paid_broadcast,
                message_effect_id=message_effect_id,
                reply_parameters=reply_parameters,
                reply_markup=reply_markup,
                **__pydantic_kwargs,
            )


class SendRichMessageDraft(TelegramMethod[bool]):
    __returning__ = bool
    __api_method__ = "sendRichMessageDraft"

    chat_id: int
    draft_id: int
    rich_message: InputRichMessage
    message_thread_id: Optional[int] = None

    if TYPE_CHECKING:

        def __init__(
            __pydantic__self__,
            *,
            chat_id: int,
            draft_id: int,
            rich_message: InputRichMessage,
            message_thread_id: Optional[int] = None,
            **__pydantic_kwargs: Any,
        ) -> None:
            super().__init__(
                chat_id=chat_id,
                draft_id=draft_id,
                rich_message=rich_message,
                message_thread_id=message_thread_id,
                **__pydantic_kwargs,
            )
