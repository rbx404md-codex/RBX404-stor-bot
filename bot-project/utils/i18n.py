"""Small, dependency-free translation layer for the user-facing navigation."""

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

LANGUAGES = {
    "bn": "বাংলা",
    "en": "English",
    "hi": "हिन्दी",
    "ur": "اردو",
    "ru": "Русский",
    "ar": "العربية",
}

TEXTS = {
    "bn": {
        "language_saved": "✅ ভাষা সংরক্ষণ হয়েছে।",
        "language_title": "🌐 আপনার ভাষা বেছে নিন:",
        "main_menu": "🏠 প্রধান মেনু",
    },
    "en": {
        "language_saved": "✅ Language saved.",
        "language_title": "🌐 Choose your language:",
        "main_menu": "🏠 Main menu",
    },
    "hi": {
        "language_saved": "✅ भाषा सहेजी गई।",
        "language_title": "🌐 अपनी भाषा चुनें:",
        "main_menu": "🏠 मुख्य मेनू",
    },
    "ur": {
        "language_saved": "✅ زبان محفوظ ہو گئی۔",
        "language_title": "🌐 اپنی زبان منتخب کریں:",
        "main_menu": "🏠 مرکزی مینو",
    },
    "ru": {
        "language_saved": "✅ Язык сохранён.",
        "language_title": "🌐 Выберите язык:",
        "main_menu": "🏠 Главное меню",
    },
    "ar": {
        "language_saved": "✅ تم حفظ اللغة.",
        "language_title": "🌐 اختر لغتك:",
        "main_menu": "🏠 القائمة الرئيسية",
    },
}


def tr(language: str | None, key: str, fallback: str | None = None) -> str:
    language = language if language in TEXTS else "bn"
    return TEXTS[language].get(key, fallback or TEXTS["bn"].get(key, key))


def language_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for code, label in LANGUAGES.items():
        kb.button(text=label, callback_data=f"language:set:{code}")
    kb.button(text="⬅️ Main Menu", callback_data="menu:main")
    kb.adjust(2, 2, 2, 1)
    return kb.as_markup()