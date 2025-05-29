# -*- coding: utf-8 -*-
import logging
from aiogram import Router, F # Import F for filtering
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.markdown import hbold

logger = logging.getLogger(__name__)
common_router = Router()

# Define Reply Keyboard Buttons
button_genre = KeyboardButton(text="🎬 اقتراح فيلم")
button_daily = KeyboardButton(text="☀️ اقتراح اليوم")
button_favorites = KeyboardButton(text="⭐ مفضلتي")
button_search_info = KeyboardButton(text="🔍 بحث") # This button might just show info

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
    user_name = message.from_user.full_name
    # Corrected the multiline f-string syntax
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

# Handlers for Reply Keyboard Buttons
# These handlers will catch the exact text from the buttons

# A better approach for handling reply keyboard buttons is to use F.text filter
# and map button text to specific command handlers or functions.
# For now, guiding the user is simpler.

@common_router.message(F.text == "🎬 اقتراح فيلم")
async def handle_genre_button(message: Message):
    """Handles the reply keyboard button for genre suggestion."""
    await message.answer("لعرض قائمة الأنواع واختيار اقتراح، يرجى استخدام الأمر /genre.")

@common_router.message(F.text == "☀️ اقتراح اليوم")
async def handle_daily_button(message: Message):
    """Handles the reply keyboard button for daily suggestion."""
    await message.answer("للحصول على اقتراح اليوم، يرجى استخدام الأمر /daily.")

@common_router.message(F.text == "⭐ مفضلتي")
async def handle_favorites_button(message: Message):
    """Handles the reply keyboard button for favorites."""
    await message.answer("لعرض قائمة المفضلة، يرجى استخدام الأمر /favorites.")

@common_router.message(F.text == "🔍 بحث")
async def handle_search_info_button(message: Message):
    """Handles the reply keyboard button for search info."""
    await message.answer("للبحث عن فيلم، ما عليك سوى كتابة اسمه أو كلمة مفتاحية في حقل الإدخال وإرسالها.")

