# -*- coding: utf-8 -*-
import logging
import random
import aiohttp
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

# Use absolute imports
from src.services import tmdb
# Removed obsolete import: from src.handlers.favorites import add_to_favorites

logger = logging.getLogger(__name__)
genre_router = Router()

# State for pagination
class GenreMovies(StatesGroup):
    showing = State()

# Cache for genres to avoid fetching every time
genre_cache = {}

async def get_genres_cached(session: aiohttp.ClientSession) -> dict:
    """Fetches genres from TMDb, using a simple cache."""
    global genre_cache
    if not genre_cache:
        genres = await tmdb.get_genres(session)
        if genres:
            genre_cache = genres
            logger.info(f"Fetched and cached genres from TMDb: {genre_cache}") # Log fetched genres
        else:
            logger.error("Failed to fetch genres from TMDb.")
            return {}
    return genre_cache

def create_genre_keyboard(genres: dict) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=name_ar, callback_data=f"genre_{genre_id}")]
        for genre_id, name_ar in genres.items()
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

@genre_router.message(Command("genre"))
async def handle_genre_command(message: Message, state: FSMContext, session: aiohttp.ClientSession):
    """Handles the /genre command, showing genre selection keyboard."""
    await state.clear()
    genres = await get_genres_cached(session)
    if not genres:
        await message.answer("عذرًا، حدث خطأ أثناء جلب أنواع الأفلام. يرجى المحاولة مرة أخرى لاحقًا.")
        return

    keyboard = create_genre_keyboard(genres)
    await message.answer("الرجاء اختيار نوع الفيلم المفضل لديك:", reply_markup=keyboard)

@genre_router.callback_query(F.data.startswith("genre_"))
async def handle_genre_selection(callback_query: CallbackQuery, state: FSMContext, session: aiohttp.ClientSession):
    """Handles the callback query when a genre button is pressed."""
    try:
        genre_id_str = callback_query.data.split("_")[1]
        genre_id = int(genre_id_str) # Convert to int
        logger.info(f"Received genre selection callback. Genre ID string: 		{genre_id_str}		, Parsed integer ID: {genre_id}")
    except (IndexError, ValueError) as e:
        logger.error(f"Error parsing genre ID from callback data 		{callback_query.data}		: {e}")
        await callback_query.answer("حدث خطأ في تحديد النوع.")
        return

    genres = await get_genres_cached(session)
    genre_name = genres.get(genre_id, "غير معروف")

    await callback_query.message.edit_text(f"لقد اخترت نوع: {genre_name}. جاري البحث عن اقتراح...")
    await callback_query.answer()

    # Check if genre_id is valid before making the API call
    if not isinstance(genre_id, int):
        logger.error(f"Invalid genre_id type ({type(genre_id)}) before calling TMDb API: {genre_id}")
        await callback_query.message.edit_text(f"عذرًا، حدث خطأ داخلي في تحديد نوع 		{genre_name}		.")
        return

    movies = await tmdb.discover_movies_by_genre(session, genre_id, page=1)

    if movies is None: # Check for API error first
        logger.error(f"TMDb API call failed for genre ID {genre_id} ({genre_name}).")
        await callback_query.message.edit_text(f"عذرًا، حدث خطأ أثناء البحث عن أفلام من نوع 		{genre_name}		.")
        return
    
    if not movies: # Check for empty results
        logger.warning(f"No movies found for genre ID {genre_id} ({genre_name}).")
        await callback_query.message.edit_text(f"عذرًا، لم يتم العثور على أفلام من نوع 		{genre_name}		 حاليًا.")
        return

    # Pick a random movie from the first page results
    movie = random.choice(movies)
    movie_id = movie.get("id")
    title = movie.get("title", "غير متوفر")
    overview = movie.get("overview", "لا يوجد وصف متاح.")
    release_date = movie.get("release_date", "غير معروف")
    rating = movie.get("vote_average", "N/A")
    poster_path = movie.get("poster_path")
    poster_url = tmdb.get_poster_url(poster_path)

    caption = (
        f"🎬 **{title}** ({release_date[:4] if release_date != 'غير معروف' else '----'})\n\n"
        f"📊 **النوع:** {genre_name}\n"
        f"⭐ **التقييم:** {rating}/10\n\n"
        f"📝 **الوصف:**\n{overview[:500] + ('...' if len(overview) > 500 else '')}"
    )

    buttons = [
        [InlineKeyboardButton(text="➕ إضافة للمفضلة", callback_data=f"add_fav_{movie_id}")],
        [InlineKeyboardButton(text="🔄 اقتراح آخر (نفس النوع)", callback_data=f"genre_{genre_id}")]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await state.update_data(current_movie=movie)

    if poster_url:
        try:
            await callback_query.message.answer_photo(photo=poster_url, caption=caption, reply_markup=keyboard)
            await callback_query.message.delete()
        except Exception as e:
            logger.warning(f"Failed to send photo for movie {movie_id}: {e}. Sending text instead.")
            await callback_query.message.edit_text(caption, reply_markup=keyboard)
    else:
        await callback_query.message.edit_text(caption, reply_markup=keyboard)

    await state.set_state(GenreMovies.showing)
    await state.update_data(genre_id=genre_id)

