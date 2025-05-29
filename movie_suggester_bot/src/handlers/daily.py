# -*- coding: utf-8 -*-
import logging
import random
import aiohttp

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.markdown import hbold, hitalic

# Use absolute imports
from src.services import tmdb, database

logger = logging.getLogger(__name__)
daily_router = Router()

async def send_daily_suggestion(message: Message, session: aiohttp.ClientSession, bot: Bot):
    """Fetches a popular movie and sends it as a daily suggestion."""
    # Add user to DB if not exists
    await database.add_user_if_not_exists(
        user_id=message.from_user.id,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        username=message.from_user.username
    )
    await message.answer("جاري البحث عن اقتراح اليوم...")

    # Fetch popular movies (consider fetching more pages or randomizing page)
    movies = await tmdb.get_popular_movies(session, page=random.randint(1, 5)) # Get from first 5 pages

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

        # Prepare actors string separately
        actors_str = ", ".join(cast_list) if cast_list else 'غير معروف'
        # Corrected caption f-string
        caption = (
            f"☀️ {hbold('اقتراح اليوم!')}\n\n"
            f"🎬 {hbold(title)}\n\n"
            f"📅 تاريخ الإصدار: {release_date}\n"
            f"⭐ التقييم: {vote_average}/10\n"
            f"🎬 المخرج: {director}\n"
            f"🎭 الممثلون: {actors_str}\n\n" # Use the pre-formatted actors string
            f"📝 الوصف: {hitalic(overview) if overview else 'لا يوجد وصف.'}"
        )

        # Add favorite button
        fav_button = InlineKeyboardButton(text="➕ إضافة للمفضلة", callback_data=f"fav_add_{movie_id}") # Pass only movie_id
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[fav_button]])

        if poster_url:
            try:
                await bot.send_photo(message.chat.id, photo=poster_url, caption=caption, reply_markup=keyboard)
            except Exception as e:
                logger.warning(f"Failed to send photo for daily suggestion movie {movie_id}. Sending text instead. Error: {e}")
                await message.answer(caption, reply_markup=keyboard)
        else:
            await message.answer(caption, reply_markup=keyboard)
    else:
        await message.answer("عذرًا، لم أتمكن من العثور على اقتراح اليوم حاليًا. يرجى المحاولة مرة أخرى لاحقًا.")

@daily_router.message(Command("daily"))
async def handle_daily_command(message: Message, session: aiohttp.ClientSession, bot: Bot):
    """Handles the /daily command."""
    await send_daily_suggestion(message, session, bot)

