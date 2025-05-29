# -*- coding: utf-8 -*-
import logging
import aiohttp
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext

# Use absolute imports
from src.services import tmdb
# Note: add_to_favorites is in handlers.favorites, which itself uses database functions.
# Direct import might be okay, but consider if search should just provide info/buttons
# that trigger the favorites handler callbacks instead of calling its functions directly.
# For now, keep the import but comment out its usage as the current logic doesn't use it.
# from src.handlers.favorites import add_to_favorites

logger = logging.getLogger(__name__)
search_router = Router()

# This handler catches any text message that is not a command
@search_router.message(F.text & ~F.text.startswith("/"))
async def handle_search_query(message: Message, state: FSMContext, session: aiohttp.ClientSession):
    """Handles text messages as potential search queries, fetching results from TMDb."""
    await state.clear() # Clear previous state
    query = message.text
    await message.answer(f"جاري البحث عن أفلام تطابق: 		{query}		...")

    results = await tmdb.search_movies(session, query, page=1)

    if results is None: # Indicates an API error
        await message.answer(f"عذرًا، حدث خطأ أثناء البحث عن 		{query}		. يرجى المحاولة مرة أخرى لاحقًا.")
        return
    
    if not results:
        await message.answer(f"لم يتم العثور على أفلام تطابق بحثك: 		{query}		.")
        return

    response_text = f"نتائج البحث عن 		{query}		:\n\n"
    # Limit results to avoid overly long messages, e.g., top 5
    max_results = 5 
    buttons = [] # Prepare for potential buttons
    for i, movie in enumerate(results[:max_results]):
        movie_id = movie.get("id")
        title = movie.get("title", "غير متوفر")
        release_date = movie.get("release_date", "غير معروف")
        year = release_date[:4] if release_date != "غير معروف" else "----"
        overview = movie.get("overview", "")
        short_overview = overview[:100] + ("..." if len(overview) > 100 else "")
        # poster_path = movie.get("poster_path") # Not used in text list
        # poster_url = tmdb.get_poster_url(poster_path)

        response_text += f"**{i+1}. {title} ({year})**\n"
        response_text += f"{short_overview}\n\n"
        
        # Add button to add this specific movie to favorites
        # This button will trigger the favorites handler callback
        buttons.append([InlineKeyboardButton(text=f"➕ إضافة 		{title[:20]}...		", callback_data=f"add_fav_{movie_id}")])

    # Add a note about limited results if necessary
    if len(results) > max_results:
        response_text += f"\n*عرض أفضل {max_results} نتائج. قد يكون هناك المزيد.*"

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(response_text, reply_markup=keyboard)

    # Store the search results (or relevant IDs/titles) in state 
    # so the add_fav callback can potentially get the title without a new API call.
    # Storing full results might be large; store necessary info like {movie_id: title}.
    search_results_summary = {m["id"]: m["title"] for m in results[:max_results]}
    await state.update_data(search_results=search_results_summary)

# Optional: Add a specific /search command if needed
# @search_router.message(Command("search"))
# async def handle_search_command(message: Message):
#     await message.answer("الرجاء كتابة اسم الفيلم أو كلمة مفتاحية للبحث عنه.")

