# -*- coding: utf-8 -*-
import logging
import asyncio

from aiogram import Router, F, Bot
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# Use absolute imports
from src.config import ADMIN_ID
from src.services.database import get_user_count, get_total_favorites_count, get_all_user_ids # Corrected import

logger = logging.getLogger(__name__)
admin_router = Router()

# Define states for broadcast message
class BroadcastState(StatesGroup):
    waiting_for_message = State()

# Filter to check if the user is the admin
def is_admin(message: Message) -> bool:
    return message.from_user.id == ADMIN_ID

@admin_router.message(Command("admin"), is_admin)
async def handle_admin_command(message: Message):
    """Handles the /admin command and shows the admin panel."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 عرض الإحصائيات", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📢 إرسال رسالة عامة", callback_data="admin_broadcast")]
        # Add more admin buttons here if needed
    ])
    await message.answer("لوحة تحكم المدير:", reply_markup=keyboard)

@admin_router.callback_query(F.data == "admin_stats", is_admin)
async def handle_stats_button(callback_query: CallbackQuery):
    """Handles the stats button press from the admin panel."""
    user_count = await get_user_count()
    favorites_count = await get_total_favorites_count()
    stats_text = f"""📊 إحصائيات البوت:
👤 إجمالي المستخدمين: {user_count}
⭐ إجمالي الأفلام المفضلة: {favorites_count}"""
    await callback_query.message.answer(stats_text)
    await callback_query.answer() # Acknowledge the callback

@admin_router.callback_query(F.data == "admin_broadcast", is_admin)
async def handle_broadcast_button(callback_query: CallbackQuery, state: FSMContext):
    """Handles the broadcast button press and asks for the message."""
    await callback_query.message.answer("يرجى إرسال الرسالة التي تود بثها لجميع المستخدمين. للإلغاء، أرسل /cancel.")
    await state.set_state(BroadcastState.waiting_for_message)
    await callback_query.answer() # Acknowledge the callback

@admin_router.message(StateFilter(BroadcastState.waiting_for_message), Command("cancel"))
async def cancel_broadcast(message: Message, state: FSMContext):
    """Cancels the broadcast operation."""
    await state.clear()
    await message.answer("تم إلغاء عملية البث.")

@admin_router.message(StateFilter(BroadcastState.waiting_for_message), is_admin)
async def process_broadcast_message(message: Message, state: FSMContext, bot: Bot):
    """Processes the broadcast message and sends it to all users."""
    broadcast_text = message.text # Or handle other content types if needed
    await state.clear()

    user_ids = await get_all_user_ids()
    if not user_ids:
        await message.answer("لا يوجد مستخدمون لإرسال الرسالة إليهم.")
        return

    await message.answer(f"بدء إرسال الرسالة إلى {len(user_ids)} مستخدم...")
    sent_count = 0
    failed_count = 0

    for user_id in user_ids:
        try:
            await bot.send_message(user_id, broadcast_text)
            sent_count += 1
            await asyncio.sleep(0.1) # Avoid hitting rate limits
        except Exception as e:
            logger.warning(f"Failed to send broadcast to user {user_id}: {e}")
            failed_count += 1

    await message.answer(f"""اكتمل البث.
✅ تم الإرسال بنجاح إلى: {sent_count} مستخدم.
❌ فشل الإرسال إلى: {failed_count} مستخدم.""")

# Fallback for non-admin users trying admin commands
@admin_router.message(Command("admin"))
async def handle_non_admin_command(message: Message):
    await message.answer("عذرًا، هذا الأمر مخصص للمدير فقط.")

