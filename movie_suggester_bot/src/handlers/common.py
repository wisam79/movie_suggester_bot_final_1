# -*- coding: utf-8 -*-
import logging
import aiohttp

from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.markdown import hbold

# Use absolute imports
from src.handlers.genre import send_genre_selection_keyboard
from src.handlers.daily import send_daily_suggestion
from src.handlers.favorites import show_favorites_list
from src.services import database # Import database service

logger = logging.getLogger(__name__)
common_router = Router()

# Define Reply Keyboard Buttons
button_genre = KeyboardButton(text="🎬 اقتراح فيلم")
button_daily = KeyboardButton(text="☀️ اقتراح اليوم")
button_favorites = KeyboardButton(text="⭐ مفضلتي")
button_search_info = KeyboardButton(text="🔍 بحث") # This button will just show info

# Define Reply Keyboard Layout
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [button_genre, button_daily],
        [button_favorites, button_search_info]
    ],
    resize_keyboard=True,
    input_field_placeholder="اختر أمرًا أو اكتب اسم فيلم للبحث..."
)

@common_router.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """This handler receives messages with `/start` command and shows the main keyboard."""
    # Add user to DB if not exists
    await database.add_user_if_not_exists(
        user_id=message.from_user.id,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        username=message.from_user.username
    )
    user_name = message.from_user.full_name
    welcome_message = (
        f"أهلاً بك يا {hbold(user_name)} في بوت اقتراح الأفلام! 👋\n\n"
        f"يمكنك استخدام الأزرار أدناه أو كتابة اسم فيلم للبحث عنه مباشرة.\n\n"
        f"الأوامر المتاحة:\n"
        f"/genre - لاختيار نوع فيلم والحصول على اقتراح.\n"
        f"/daily - للحصول على اقتراح فيلم شائع.\n"
        f"/favorites - لعرض وإدارة قائمة أفلامك المفضلة.\n\n"
        f"اكتب اسم فيلم أو كلمة مفتاحية للبحث."
    )
    await message.answer(welcome_message, reply_markup=main_keyboard)

# Handlers for Reply Keyboard Buttons - Direct Execution

@common_router.message(F.text == "🎬 اقتراح فيلم")
async def handle_genre_button(message: Message, session: aiohttp.ClientSession):
    """Handles the reply keyboard button for genre suggestion by directly showing the keyboard."""
    await send_genre_selection_keyboard(message, session)

@common_router.message(F.text == "☀️ اقتراح اليوم")
async def handle_daily_button(message: Message, session: aiohttp.ClientSession, bot: Bot):
    """Handles the reply keyboard button for daily suggestion by directly sending a suggestion."""
    await send_daily_suggestion(message, session, bot)

@common_router.message(F.text == "⭐ مفضلتي")
async def handle_favorites_button(message: Message, session: aiohttp.ClientSession, bot: Bot):
    """Handles the reply keyboard button for favorites by directly showing the list."""
    await show_favorites_list(message, session, bot)

@common_router.message(F.text == "🔍 بحث")
async def handle_search_info_button(message: Message):
    """Handles the reply keyboard button for search info."""
    await message.answer("للبحث عن فيلم، ما عليك سوى كتابة اسمه أو كلمة مفتاحية في حقل الإدخال وإرسالها.")

