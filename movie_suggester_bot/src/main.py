# -*- coding: utf-8 -*-
import asyncio
import logging
import aiohttp

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties # Import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

# Use absolute imports based on the project structure when running as a module
from src.config import TELEGRAM_BOT_TOKEN
from src.services import database
from src.handlers.common import common_router
from src.handlers.genre import genre_router
from src.handlers.daily import daily_router
from src.handlers.favorites import favorites_router
from src.handlers.search import search_router
from src.handlers.admin import admin_router # Import the admin router

# Configure logging
logging.basicConfig(level=logging.INFO, format=	'%(asctime)s - %(name)s - %(levelname)s - %(message)s	')
logger = logging.getLogger(__name__)

async def main():
    # Initialize database
    await database.init_db()

    # Initialize Bot and Dispatcher with new default properties method
    bot = Bot(token=TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode="Markdown")) # New way
    
    # Use MemoryStorage for FSM states for simplicity, can be changed later
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Create a single aiohttp session to be used across handlers
    async with aiohttp.ClientSession() as session:
        # Pass the session and bot instance to the dispatcher context
        dp["session"] = session
        # dp["bot"] = bot # Pass bot instance if needed directly in handlers (e.g., for broadcast)
        # Note: Passing bot via context is less common now; aiogram provides it via handler args

        # Register routers
        # Order matters if handlers overlap (e.g., search catching all text)
        dp.include_router(admin_router) # Register admin router first
        dp.include_router(common_router)
        dp.include_router(genre_router)
        dp.include_router(daily_router)
        dp.include_router(favorites_router)
        dp.include_router(search_router) # Register search last as it catches generic text

        # Start polling
        logger.info("Starting bot polling...")
        # Remove any pending updates
        await bot.delete_webhook(drop_pending_updates=True)
        # Pass bot instance directly to start_polling if needed by handlers like broadcast
        await dp.start_polling(bot, session=session) # Pass session here too

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped manually.")
    except Exception as e:
        logger.critical(f"Bot crashed with error: {e}", exc_info=True)

