# -*- coding: utf-8 -*-
import logging
import asyncio
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message

# Use absolute imports
from src.config import ADMIN_ID
from src.services.database import get_user_count_db, get_total_favorites_count_db, get_all_user_ids_db

logger = logging.getLogger(__name__)
admin_router = Router()

# Middleware or filter to check if the user is the admin
# This filter will be applied to all handlers in this router
admin_router.message.filter(F.from_user.id == ADMIN_ID)
admin_router.callback_query.filter(F.from_user.id == ADMIN_ID)

@admin_router.message(Command("admin"))
async def handle_admin_command(message: Message):
    """Shows available admin commands."""
    admin_help_text = (
        "أهلاً بك في لوحة تحكم المدير!\n\n"
        "الأوامر المتاحة:\n"
        "/stats - لعرض إحصائيات استخدام البوت.\n"
        "/broadcast <الرسالة> - لإرسال رسالة لجميع المستخدمين."
    )
    await message.answer(admin_help_text)

@admin_router.message(Command("stats"))
async def handle_stats_command(message: Message):
    """Handles the /stats command, showing bot statistics."""
    try:
        user_count = await get_user_count_db()
        favorites_count = await get_total_favorites_count_db()
        stats_text = (
            f"📊 **إحصائيات البوت:**\n\n"
            f"👤 إجمالي المستخدمين المسجلين: {user_count}\n"
            f"⭐ إجمالي الأفلام في المفضلة (لكل المستخدمين): {favorites_count}"
        )
        await message.answer(stats_text)
    except Exception as e:
        logger.error(f"Error fetching stats: {e}", exc_info=True)
        await message.answer("حدث خطأ أثناء جلب الإحصائيات.")

@admin_router.message(Command("broadcast"))
async def handle_broadcast_command(message: Message, bot: Bot):
    """Handles the /broadcast command to send a message to all users."""
    broadcast_message = message.text.split("/broadcast", 1)[1].strip()
    if not broadcast_message:
        await message.answer("يرجى كتابة الرسالة التي تريد إرسالها بعد الأمر /broadcast.")
        return

    try:
        user_ids = await get_all_user_ids_db()
        if not user_ids:
            await message.answer("لا يوجد مستخدمون مسجلون لإرسال الرسالة إليهم.")
            return

        await message.answer(f"جاري إرسال الرسالة إلى {len(user_ids)} مستخدمًا...")
        sent_count = 0
        failed_count = 0

        for user_id in user_ids:
            try:
                # Corrected the f-string syntax
                await bot.send_message(user_id, f"رسالة من مدير البوت:\n\n{broadcast_message}")
                sent_count += 1
                # Add a small delay to avoid hitting Telegram rate limits
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.warning(f"Failed to send broadcast message to user {user_id}: {e}")
                failed_count += 1

        await message.answer(
            f"اكتمل الإرسال.\n"
            f"✅ تم الإرسال بنجاح إلى: {sent_count} مستخدمًا.\n"
            f"❌ فشل الإرسال إلى: {failed_count} مستخدمًا."
        )
    except Exception as e:
        logger.error(f"Error during broadcast: {e}", exc_info=True)
        await message.answer("حدث خطأ أثناء عملية الإرسال الجماعي.")

