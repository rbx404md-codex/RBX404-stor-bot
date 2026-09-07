"""Telegram transport with one consistent custom-emoji rendering layer."""
from typing import Any

from aiogram import Bot

from utils.branding import render_custom_emojis


class BrandedBot(Bot):
    """Render custom emoji for every user-visible Bot API text/caption.

    Inline keyboard labels intentionally keep their Unicode fallback: the
    Bot API does not expose message-entity parsing for button text.
    """

    @staticmethod
    def _render_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
        # Explicit parse_mode=None is used for user-authored plain text
        # (notably broadcasts). Do not turn arbitrary user input into HTML.
        if kwargs.get("parse_mode") is None and "parse_mode" in kwargs:
            return kwargs

        rendered = dict(kwargs)
        for field in ("text", "caption"):
            value = rendered.get(field)
            if isinstance(value, str):
                rendered[field] = render_custom_emojis(value)
        # Make the custom-emoji HTML mode explicit. Relying only on
        # DefaultBotProperties is fragile when Message.answer forwards
        # through a subclassed Bot method.
        if "parse_mode" not in rendered and "entities" not in rendered and "caption_entities" not in rendered:
            rendered["parse_mode"] = "HTML"
        return rendered

    async def send_message(self, *args: Any, **kwargs: Any) -> Any:
        return await super().send_message(*args, **self._render_kwargs(kwargs))

    async def send_photo(self, *args: Any, **kwargs: Any) -> Any:
        return await super().send_photo(*args, **self._render_kwargs(kwargs))

    async def send_document(self, *args: Any, **kwargs: Any) -> Any:
        return await super().send_document(*args, **self._render_kwargs(kwargs))

    async def send_video(self, *args: Any, **kwargs: Any) -> Any:
        return await super().send_video(*args, **self._render_kwargs(kwargs))

    async def send_audio(self, *args: Any, **kwargs: Any) -> Any:
        return await super().send_audio(*args, **self._render_kwargs(kwargs))

    async def send_voice(self, *args: Any, **kwargs: Any) -> Any:
        return await super().send_voice(*args, **self._render_kwargs(kwargs))

    async def send_animation(self, *args: Any, **kwargs: Any) -> Any:
        return await super().send_animation(*args, **self._render_kwargs(kwargs))

    async def edit_message_text(self, *args: Any, **kwargs: Any) -> Any:
        return await super().edit_message_text(*args, **self._render_kwargs(kwargs))

    async def edit_message_caption(self, *args: Any, **kwargs: Any) -> Any:
        return await super().edit_message_caption(*args, **self._render_kwargs(kwargs))