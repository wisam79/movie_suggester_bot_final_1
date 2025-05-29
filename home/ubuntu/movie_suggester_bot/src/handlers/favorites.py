# -*- coding: utf-8 -*-
import logging
import aiohttp
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

# Use absolute imports
from src.services import tmdb # Import tmdb service
from src.services.database import add_favorite_db, remove_favorite_db, get_favorites_db

logger = logging.getLogger(__name__)
favorites_router = Router()

# This handler now relies on the database service placeholders

@favorites_router.message(Command("favorites"))
async def handle_favorites_command(message: Message, session: aiohttp.ClientSession):
    """Handles the /favorites command, showing the user's favorite movies from DB."""
    user_id = message.from_user.id
    favorite_movie_ids = await get_favorites_db(user_id)

    if not favorite_movie_ids:
        await message.answer("قائمة المفضلة فارغة حاليًا. يمكنك إضافة أفلام إليها عند تصفح الاقتراحات أو البحث.")
        return

    response_text = "قائمة أفلامك المفضلة:\n\n"
    buttons = []
    movies_details = []

    # Fetch details for each favorite movie ID
    for movie_id in favorite_movie_ids:
        movie_detail = await tmdb.get_movie_details(session, movie_id)
        if movie_detail:
            movies_details.append(movie_detail)
        else:
            logger.warning(f"Could not fetch details for favorite movie ID: {movie_id} for user {user_id}")
            # Optionally remove invalid ID from DB here or notify user

    if not movies_details:
        await message.answer("عذرًا، حدث خطأ أثناء جلب تفاصيل أفلامك المفضلة.")
        return

    for movie in movies_details:
        title = movie.get("title", "غير متوفر")
        year = movie.get("release_date", "----")[0:4]
        movie_id = movie.get("id")
        response_text += f"- {title} ({year})\n"
        buttons.append([InlineKeyboardButton(text=f"إزالة 🗑️ - {title}", callback_data=f"remove_fav_{movie_id}")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(response_text, reply_markup=keyboard)

# Callback handler for adding favorites (triggered by buttons from other handlers)
@favorites_router.callback_query(F.data.startswith("add_fav_"))
async def handle_add_favorite_callback(callback_query: CallbackQuery, state: FSMContext, session: aiohttp.ClientSession):
    user_id = callback_query.from_user.id
    try:
        movie_id = int(callback_query.data.split("_")[2])
    except (IndexError, ValueError):
        logger.error(f"Invalid callback data for add_fav: {callback_query.data}")
        await callback_query.answer("حدث خطأ.")
        return

    # Try to get movie title from state first (set by the handler that showed the movie)
    state_data = await state.get_data()
    movie_title = None
    current_movie = state_data.get("current_movie")
    if current_movie and current_movie.get("id") == movie_id:
        movie_title = current_movie.get("title")
    
    # If not in state, fetch from TMDb
    if not movie_title:
        movie_details = await tmdb.get_movie_details(session, movie_id)
        if movie_details:
            movie_title = movie_details.get("title", f"فيلم ID:{movie_id}")
        else:
            await callback_query.answer("عذرًا، لم يتم العثور على تفاصيل الفيلم.")
            return

    added = await add_favorite_db(user_id, movie_id, movie_title) # Use DB function

    if added is None: # Assume None means DB error
        await callback_query.answer("حدث خطأ أثناء محاولة إضافة الفيلم للمفضلة.")
    elif added:
        await callback_query.answer(f"تمت إضافة 		{movie_title}		 إلى المفضلة!")
    else:
        await callback_query.answer(f"		{movie_title}		 موجودة بالفعل في المفضلة.")

# Callback handler for removing favorites
@favorites_router.callback_query(F.data.startswith("remove_fav_"))
async def handle_remove_favorite_callback(callback_query: CallbackQuery, session: aiohttp.ClientSession):
    user_id = callback_query.from_user.id
    try:
        movie_id_to_remove = int(callback_query.data.split("_")[2])
    except (IndexError, ValueError):
        logger.error(f"Invalid callback data for remove_fav: {callback_query.data}")
        await callback_query.answer("حدث خطأ.")
        return

    removed = await remove_favorite_db(user_id, movie_id_to_remove) # Use DB function

    if removed is None: # Assume None means DB error
        await callback_query.answer("حدث خطأ أثناء محاولة إزالة الفيلم من المفضلة.")
    elif removed:
        await callback_query.answer("تمت إزالة الفيلم من المفضلة.")
        # Refresh the favorites list message by editing the existing one
        # Need to call handle_favorites_command logic again, but edit the message
        # For simplicity, we'll just edit the text to confirm removal and ask user to re-run /favorites
        # A better approach would be to re-fetch and rebuild the message content and keyboard
        await callback_query.message.edit_text("تمت إزالة الفيلم بنجاح. لعرض القائمة المحدثة، استخدم الأمر /favorites مرة أخرى.", reply_markup=None)
    else:
        await callback_query.answer("لم يتم العثور على الفيلم في المفضلة أو حدث خطأ.")

