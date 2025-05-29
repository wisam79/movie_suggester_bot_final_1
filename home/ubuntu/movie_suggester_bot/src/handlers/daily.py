# -*- coding: utf-8 -*-
import logging
import random
import aiohttp
from aiogram import Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

# Use absolute imports
from src.services import tmdb


logger = logging.getLogger(__name__)
daily_router = Router()

@daily_router.message(Command("daily"))
async def handle_daily_command(message: Message, state: FSMContext, session: aiohttp.ClientSession):
    """Handles the /daily command, providing a popular movie suggestion."""
    await state.clear() # Clear previous state
    await message.answer("جاري البحث عن اقتراح اليوم...")

    # Fetch popular movies from TMDb (e.g., from the first few pages)
    movies = []
    for page in range(1, 4): # Check first 3 pages for variety
        page_movies = await tmdb.get_popular_movies(session, page=page)
        if page_movies:
            movies.extend(page_movies)
        else:
            # Stop if a page fails or has no results
            break

    if not movies:
        await message.answer("عذرًا، لم أتمكن من العثور على اقتراح فيلم شائع في الوقت الحالي. يرجى المحاولة مرة أخرى لاحقًا.")
        return

    # Pick a random movie from the fetched popular movies
    movie = random.choice(movies)
    movie_id = movie.get("id")
    title = movie.get("title", "غير متوفر")
    overview = movie.get("overview", "لا يوجد وصف متاح.")
    release_date = movie.get("release_date", "غير معروف")
    rating = movie.get("vote_average", "N/A")
    poster_path = movie.get("poster_path")
    poster_url = tmdb.get_poster_url(poster_path)

    caption = (
        f"✨ **اقتراح اليوم** ✨\n\n"
        f"🎬 **{title}** ({release_date[:4] if release_date != 'غير معروف' else '----'})\n\n"
        f"⭐ **التقييم:** {rating}/10\n\n"
        f"📝 **الوصف:**\n{overview[:500] + ('...' if len(overview) > 500 else '')}"
    )

    # Add button: Add to Favorites
    buttons = [
        [InlineKeyboardButton(text="➕ إضافة للمفضلة", callback_data=f"add_fav_{movie_id}")]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    # Store movie data in state for potential use by favorites callback
    await state.update_data(current_movie=movie)

    if poster_url:
        try:
            await message.answer_photo(photo=poster_url, caption=caption, reply_markup=keyboard)
        except Exception as e:
            logger.warning(f"Failed to send photo for daily movie {movie_id}: {e}. Sending text instead.")
            await message.answer(caption, reply_markup=keyboard)
    else:
        await message.answer(caption, reply_markup=keyboard)

