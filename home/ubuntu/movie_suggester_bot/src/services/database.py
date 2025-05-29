# -*- coding: utf-8 -*-
import aiosqlite
import logging
import os
from typing import List, Optional, Tuple

# Use absolute import
from src.config import DATABASE_PATH

logger = logging.getLogger(__name__)

async def initialize_db():
    """Initializes the SQLite database and creates tables if they don\t exist."""
    # Ensure the data directory exists
    db_dir = os.path.dirname(DATABASE_PATH)
    if not os.path.exists(db_dir):
        try:
            os.makedirs(db_dir)
            logger.info(f"Created database directory: {db_dir}")
        except OSError as e:
            logger.error(f"Error creating database directory {db_dir}: {e}")
            return # Stop if directory cannot be created

    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            # Create favorites table (user_id, movie_id, movie_title, added_timestamp)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS favorites (
                    user_id INTEGER NOT NULL,
                    movie_id INTEGER NOT NULL,
                    movie_title TEXT,
                    added_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, movie_id)
                )
            """)
            # Create users table (user_id, first_name, last_name, username, first_seen_timestamp)
            # This table helps track users for stats and broadcast
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    first_name TEXT,
                    last_name TEXT,
                    username TEXT,
                    first_seen_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()
            logger.info(f"Database initialized successfully at {DATABASE_PATH}")
    except aiosqlite.Error as e:
        logger.error(f"Error initializing database at {DATABASE_PATH}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error during database initialization: {e}", exc_info=True)

async def add_user_if_not_exists(user_id: int, first_name: Optional[str], last_name: Optional[str], username: Optional[str]):
    """Adds a user to the users table if they don\t already exist."""
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute("""
                INSERT OR IGNORE INTO users (user_id, first_name, last_name, username)
                VALUES (?, ?, ?, ?)
            """, (user_id, first_name, last_name, username))
            await db.commit()
            logger.debug(f"Checked/added user {user_id} to users table.")
    except aiosqlite.Error as e:
        logger.error(f"Error adding user {user_id} to database: {e}")
    except Exception as e:
        logger.error(f"Unexpected error adding user {user_id}: {e}", exc_info=True)

async def add_favorite_db(user_id: int, movie_id: int, movie_title: Optional[str]) -> Optional[bool]:
    """Adds a movie to a user\s favorites list. Returns True if added, False if already exists, None on error."""
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            # Check if already exists
            async with db.execute("SELECT 1 FROM favorites WHERE user_id = ? AND movie_id = ?", (user_id, movie_id)) as cursor:
                exists = await cursor.fetchone()
                if exists:
                    logger.info(f"Movie {movie_id} already in favorites for user {user_id}.")
                    return False
            
            # Insert if not exists
            await db.execute("INSERT INTO favorites (user_id, movie_id, movie_title) VALUES (?, ?, ?)", (user_id, movie_id, movie_title))
            await db.commit()
            logger.info(f"Added movie {movie_id} ({movie_title}) to favorites for user {user_id}.")
            return True
    except aiosqlite.Error as e:
        logger.error(f"Error adding favorite movie {movie_id} for user {user_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error adding favorite {movie_id} for user {user_id}: {e}", exc_info=True)
        return None

async def remove_favorite_db(user_id: int, movie_id: int) -> Optional[bool]:
    """Removes a movie from a user\s favorites list. Returns True if removed, False if not found, None on error."""
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute("DELETE FROM favorites WHERE user_id = ? AND movie_id = ?", (user_id, movie_id))
            await db.commit()
            if cursor.rowcount > 0:
                logger.info(f"Removed movie {movie_id} from favorites for user {user_id}.")
                return True
            else:
                logger.warning(f"Attempted to remove non-existent favorite movie {movie_id} for user {user_id}.")
                return False
    except aiosqlite.Error as e:
        logger.error(f"Error removing favorite movie {movie_id} for user {user_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error removing favorite {movie_id} for user {user_id}: {e}", exc_info=True)
        return None

async def get_favorites_db(user_id: int) -> Optional[List[int]]:
    """Retrieves a list of movie IDs favorited by a user. Returns list or None on error."""
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            async with db.execute("SELECT movie_id FROM favorites WHERE user_id = ? ORDER BY added_timestamp DESC", (user_id,)) as cursor:
                rows = await cursor.fetchall()
                return [row[0] for row in rows]
    except aiosqlite.Error as e:
        logger.error(f"Error retrieving favorites for user {user_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error retrieving favorites for user {user_id}: {e}", exc_info=True)
        return None

# --- Functions for Admin Panel --- 

async def get_user_count_db() -> Optional[int]:
    """Gets the total number of registered users."""
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            async with db.execute("SELECT COUNT(*) FROM users") as cursor:
                result = await cursor.fetchone()
                return result[0] if result else 0
    except aiosqlite.Error as e:
        logger.error(f"Error getting user count: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting user count: {e}", exc_info=True)
        return None

async def get_total_favorites_count_db() -> Optional[int]:
    """Gets the total number of favorited movies across all users."""
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            async with db.execute("SELECT COUNT(*) FROM favorites") as cursor:
                result = await cursor.fetchone()
                return result[0] if result else 0
    except aiosqlite.Error as e:
        logger.error(f"Error getting total favorites count: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting total favorites count: {e}", exc_info=True)
        return None

async def get_all_user_ids_db() -> Optional[List[int]]:
    """Retrieves a list of all registered user IDs for broadcasting."""
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            # Ensure users are added whenever they interact (e.g., in /start or other handlers)
            # This query assumes the users table is populated.
            async with db.execute("SELECT user_id FROM users") as cursor:
                rows = await cursor.fetchall()
                return [row[0] for row in rows]
    except aiosqlite.Error as e:
        logger.error(f"Error retrieving all user IDs: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error retrieving all user IDs: {e}", exc_info=True)
        return None

