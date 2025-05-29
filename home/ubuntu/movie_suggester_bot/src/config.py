# -*- coding: utf-8 -*-
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Telegram Bot Token
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("No TELEGRAM_BOT_TOKEN found in environment variables")

# TMDb API Key
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
if not TMDB_API_KEY:
    raise ValueError("No TMDB_API_KEY found in environment variables")

# Admin User ID (Replace with your actual Telegram User ID)
ADMIN_ID = int(os.getenv("ADMIN_ID", "7813451177")) # Default to the ID provided by user

# Database Path
DATABASE_PATH = os.getenv("DATABASE_PATH", "/home/ubuntu/movie_suggester_bot/data/bot_data.db")

