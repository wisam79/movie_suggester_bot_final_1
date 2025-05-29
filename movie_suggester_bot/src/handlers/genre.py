# -*- coding: utf-8 -*-
import logging
import random
import aiohttp

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.utils.markdown import hbold, hitalic, hlink

# Use absolute imports
from src.services import tmdb, database
from src.config import ADMIN_ID # Import ADMIN_ID

logger = logging.getLogger(__name__)
genre_router = Router()

# Cache for genres to avoid frequent API calls
genre_cache: dict[int, str] = {}

async def get_genres_cached(session: aiohttp.ClientSession) -> dict[int, str]:
    """Returns genres from cache or fetches them if cache is empty."""
    global genre_cache
    if not genre_cache:
        genres = await tmdb.get_genres(session)
        if genres:
            genre_cache = genres
            logger.info(f"Fetched and cached genres from TMDb: {genre_cache}")
        else:
            logger.warning("Failed to fetch genres from TMDb.")
            return {} # Return empty dict on failure
    return genre_cache

async def build_genre_keyboard(session: aiohttp.ClientSession) -> InlineKeyboardMarkup:
    """Builds the inline keyboard with genre buttons."""
    genres = await get_genres_cached(session)
    buttons = []
    row = []
    # Sort genres alphabetically by name for consistent order
    sorted_genres = sorted(genres.items(), key=lambda item: item[1])
    for genre_id, genre_name in sorted_genres:
        row.append(InlineKeyboardButton(text=genre_name, callback_data=f"genre_{genre_id}"))
        if len(row) == 2: # Adjust number of columns if needed
            buttons.append(row)
            row = []
    if row: # Add the last row if it has buttons
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)

async def send_genre_selection_keyboard(message: Message, session: aiohttp.ClientSession):
    """Sends the message with the genre selection keyboard."""
    # Add user to DB if not exists
    await database.add_user_if_not_exists(
        user_id=message.from_user.id,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        username=message.from_user.username
    )
    keyboard = await build_genre_keyboard(session)
    if not keyboard.inline_keyboard: # Check if keyboard is empty (fetch failed)
        await message.answer("عذرًا، لم أتمكن من جلب قائمة الأنواع حاليًا. يرجى المحاولة مرة أخرى لاحقًا.")
        return
    await message.answer("الرجاء اختيار نوع الفيلم المفضل لديك:", reply_markup=keyboard)

@genre_router.message(Command("genre"))
async def handle_genre_command(message: Message, session: aiohttp.ClientSession):
    """Handles the /genre command."""
    await send_genre_selection_keyboard(message, session)

@genre_router.callback_query(F.data.startswith("genre_"))
async def handle_genre_selection(callback_query: CallbackQuery, session: aiohttp.ClientSession, bot: Bot):
    """Handles the selection of a genre from the inline keyboard."""
    genre_id_str = callback_query.data.split("_")[1]
    try:
        genre_id = int(genre_id_str)
        logger.info(f"Received genre selection callback. Genre ID string: {genre_id_str}, Parsed integer ID: {genre_id}")
    except (ValueError, IndexError):
        logger.error(f"Invalid genre callback data received: {callback_query.data}")
        await callback_query.answer("حدث خطأ غير متوقع.", show_alert=True)
        return

    genres = await get_genres_cached(session)
    genre_name = genres.get(genre_id, "غير معروف")

    await callback_query.message.edit_text(f"جاري البحث عن فيلم من نوع: {hbold(genre_name)}...")

    movies = await tmdb.discover_movies_by_genre(session, genre_id)

    if movies:
        selected_movie = random.choice(movies)
        movie_id = selected_movie.get("id")
        title = selected_movie.get("title", "غير متوفر")
        overview = selected_movie.get("overview", "لا يوجد وصف متاح.")
        release_date = selected_movie.get("release_date", "غير معروف")
        vote_average = selected_movie.get("vote_average", 0)
        poster_path = selected_movie.get("poster_path")
        poster_url = tmdb.get_poster_url(poster_path)

        # Fetch more details (optional, for director/cast)
        details = await tmdb.get_movie_details(session, movie_id)
        director = "غير معروف"
        cast_list = []
        if details and details.get("credits"):
            crew = details["credits"].get("crew", [])
            cast = details["credits"].get("cast", [])
            for member in crew:
                if member.get("job") == "Director":
                    director = member.get("name", "غير معروف")
                    break
            cast_list = [actor.get("name") for actor in cast[:5]] # Top 5 actors

        # Corrected caption f-string (used single quotes for join separator)
        caption = (
            f"🎬 {hbold(title)}\n\n"
            f"📅 تاريخ الإصدار: {release_date}\n"
            f"⭐ التقييم: {vote_average}/10\n"
            f"🎬 المخرج: {director}\n"
            f"🎭 الممثلون: {', '.join(cast_list) if cast_list else 'غير معروف'}\n\n"
            f"📝 الوصف: {hitalic(overview) if overview else 'لا يوجد وصف.'}"
        )

        # Add favorite button
        fav_button = InlineKeyboardButton(text="➕ إضافة للمفضلة", callback_data=f"fav_add_{movie_id}") # Pass only movie_id
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[fav_button]])

        if poster_url:
            try:
                await callback_query.message.delete() # Delete the "Searching..." message
                await bot.send_photo(callback_query.from_user.id, photo=poster_url, caption=caption, reply_markup=keyboard)
            except Exception as e:
                logger.warning(f"Failed to send photo for movie {movie_id}. Sending text instead. Error: {e}")
                await bot.send_message(callback_query.from_user.id, caption, reply_markup=keyboard)
        else:
            await callback_query.message.edit_text(caption, reply_markup=keyboard)

    else:
        await callback_query.message.edit_text(f"عذرًا، لم يتم العثور على أفلام من نوع {hbold(genre_name)} حاليًا أو حدث خطأ.")

    await callback_query.answer() # Acknowledge the callback query

