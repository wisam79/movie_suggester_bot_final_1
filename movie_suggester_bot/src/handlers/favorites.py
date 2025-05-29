# -*- coding: utf-8 -*-
import logging
import aiohttp

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.utils.markdown import hbold, hitalic

# Use absolute imports
from src.services import tmdb, database

logger = logging.getLogger(__name__)
favorites_router = Router()

async def show_favorites_list(message: Message, session: aiohttp.ClientSession, bot: Bot):
    """Displays the user's favorite movies with remove buttons."""
    user_id = message.from_user.id
    # Add user to DB if not exists
    await database.add_user_if_not_exists(
        user_id=user_id,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        username=message.from_user.username
    )

    # Fetch favorites with titles from DB
    favorite_movies = await database.get_favorites_with_titles_db(user_id)

    if not favorite_movies:
        await message.answer("قائمة المفضلة فارغة حاليًا. يمكنك إضافة أفلام إليها من خلال الاقتراحات.")
        return

    await message.answer("قائمة أفلامك المفضلة:")

    for movie_id, movie_title in favorite_movies:
        # Fetch details for poster and release date (optional, could be stored too)
        details = await tmdb.get_movie_details(session, movie_id)
        release_date = "غير معروف"
        poster_url = None
        if details:
            release_date = details.get("release_date", "غير معروف")
            poster_path = details.get("poster_path")
            poster_url = tmdb.get_poster_url(poster_path)

        caption = f"🎬 {hbold(movie_title)} ({release_date[:4] if release_date else 'N/A'})"
        remove_button = InlineKeyboardButton(text="❌ إزالة", callback_data=f"fav_rem_{movie_id}")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[remove_button]])

        if poster_url:
            try:
                # Send to user's chat ID directly
                await bot.send_photo(user_id, photo=poster_url, caption=caption, reply_markup=keyboard)
            except Exception as e:
                logger.warning(f"Failed to send photo for favorite movie {movie_id}. Sending text. Error: {e}")
                await bot.send_message(user_id, caption, reply_markup=keyboard)
        else:
            await bot.send_message(user_id, caption, reply_markup=keyboard)

@favorites_router.message(Command("favorites"))
async def handle_favorites_command(message: Message, session: aiohttp.ClientSession, bot: Bot):
    """Handles the /favorites command."""
    await show_favorites_list(message, session, bot)

@favorites_router.callback_query(F.data.startswith("fav_add_"))
async def handle_add_favorite(callback_query: CallbackQuery, session: aiohttp.ClientSession):
    """Handles adding a movie to favorites via inline button. Fetches full title first."""
    try:
        parts = callback_query.data.split("_", 2) # Only need fav_add_MOVIEID
        movie_id = int(parts[2])
    except (IndexError, ValueError):
        logger.error(f"Invalid fav_add callback data: {callback_query.data}")
        await callback_query.answer("خطأ في بيانات الإضافة.", show_alert=True)
        return

    user_id = callback_query.from_user.id

    # Fetch movie details to get the full title
    details = await tmdb.get_movie_details(session, movie_id)
    if not details or not details.get("title"):
        logger.error(f"Could not fetch details or title for movie ID {movie_id} to add to favorites.")
        await callback_query.answer("عذرًا، لم أتمكن من جلب تفاصيل الفيلم للإضافة.", show_alert=True)
        return

    movie_title = details["title"]

    # Add to database using the fetched full title
    added = await database.add_favorite_db(user_id, movie_id, movie_title)

    if added is True:
        await callback_query.answer(f"تمت إضافة '{movie_title}' إلى المفضلة بنجاح!", show_alert=False) # Less intrusive alert
        # Optionally, edit the original message to show confirmation or remove button
        try:
            # Create a new keyboard without the add button, maybe add a remove button?
            # For simplicity, just remove the keyboard
            await callback_query.message.edit_reply_markup(reply_markup=None)
        except Exception as e:
            logger.warning(f"Could not edit message after adding favorite: {e}")
    elif added is False:
        await callback_query.answer("هذا الفيلم موجود بالفعل في المفضلة.", show_alert=True)
    else:
        await callback_query.answer("حدث خطأ أثناء إضافة الفيلم للمفضلة.", show_alert=True)

@favorites_router.callback_query(F.data.startswith("fav_rem_"))
async def handle_remove_favorite(callback_query: CallbackQuery, session: aiohttp.ClientSession, bot: Bot):
    """Handles removing a movie from favorites via inline button."""
    try:
        movie_id = int(callback_query.data.split("_")[2])
    except (IndexError, ValueError):
        logger.error(f"Invalid fav_rem callback data: {callback_query.data}")
        await callback_query.answer("خطأ في بيانات الإزالة.", show_alert=True)
        return

    user_id = callback_query.from_user.id
    removed = await database.remove_favorite_db(user_id, movie_id)

    if removed is True:
        await callback_query.answer("تمت إزالة الفيلم من المفضلة بنجاح!", show_alert=False) # Less intrusive
        # Remove the message containing the removed favorite
        try:
            await callback_query.message.delete()
        except Exception as e:
            logger.warning(f"Could not delete favorite message after removal: {e}")
            # Optionally edit text if delete fails
            await callback_query.message.edit_text("تمت إزالة هذا الفيلم.", reply_markup=None)

    elif removed is False:
        await callback_query.answer("الفيلم غير موجود في المفضلة.", show_alert=True)
    else:
        await callback_query.answer("حدث خطأ أثناء إزالة الفيلم من المفضلة.", show_alert=True)

