# -*- coding: utf-8 -*-
import aiosqlite
import logging
import os

logger = logging.getLogger(__name__)
DB_DIR = "/home/ubuntu/movie_suggester_bot/data"
DB_PATH = os.path.join(DB_DIR, "bot_data.db")

async def init_db():
    """Initializes the database and creates tables if they don't exist."""
    os.makedirs(DB_DIR, exist_ok=True)
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Create users table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    first_name TEXT,
                    last_name TEXT,
                    username TEXT,
                    join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Create favorites table (ensure movie_title and add_date exist)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS favorites (
                    user_id INTEGER,
                    movie_id INTEGER,
                    movie_title TEXT,
                    add_date TIMESTAMP, -- Removed default here
                    PRIMARY KEY (user_id, movie_id),
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)

            # Check columns and add if missing
            cursor = await db.execute("PRAGMA table_info(favorites)")
            columns = [column[1] for column in await cursor.fetchall()]

            if 'movie_title' not in columns:
                logger.info("Adding missing 'movie_title' column to 'favorites' table.")
                await db.execute("ALTER TABLE favorites ADD COLUMN movie_title TEXT")

            if 'add_date' not in columns:
                logger.info("Adding missing 'add_date' column to 'favorites' table (without default).")
                # Add without default value to comply with SQLite limitations
                await db.execute("ALTER TABLE favorites ADD COLUMN add_date TIMESTAMP")

            await db.commit() # Commit after all checks and alterations
            logger.info(f"Database initialized successfully at {DB_PATH}")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

async def add_favorite_db(user_id: int, movie_id: int, movie_title: str) -> bool | None:
    """Adds a movie to the user's favorites list, setting add_date explicitly."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Check if already favorited
            async with db.execute("SELECT 1 FROM favorites WHERE user_id = ? AND movie_id = ?", (user_id, movie_id)) as cursor:
                if await cursor.fetchone():
                    return False # Already exists

            # Insert new favorite, setting add_date explicitly
            await db.execute(
                "INSERT INTO favorites (user_id, movie_id, movie_title, add_date) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
                (user_id, movie_id, movie_title)
            )
            await db.commit()
            logger.info(f"Added movie {movie_id} ('{movie_title}') to favorites for user {user_id}")
            return True
    except Exception as e:
        logger.error(f"Error adding favorite movie {movie_id} for user {user_id}: {e}")
        return None # Indicate error

async def get_favorites_with_titles_db(user_id: int) -> list[tuple[int, str]]:
    """Retrieves the list of favorite movie IDs and titles for a user."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Ensure the query uses the add_date column now that it should exist
            async with db.execute("SELECT movie_id, movie_title FROM favorites WHERE user_id = ? ORDER BY add_date DESC", (user_id,)) as cursor:
                rows = await cursor.fetchall()
                # Ensure movie_title is handled if it's somehow NULL
                return [(row[0], row[1] if row[1] else "عنوان غير معروف") for row in rows]
    except Exception as e:
        logger.error(f"Error getting favorites with titles for user {user_id}: {e}")
        # Return empty list on error, log should indicate the problem (e.g., missing add_date if init failed)
        return []

async def remove_favorite_db(user_id: int, movie_id: int) -> bool | None:
    """Removes a movie from the user's favorites list."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("DELETE FROM favorites WHERE user_id = ? AND movie_id = ?", (user_id, movie_id))
            await db.commit()
            if cursor.rowcount > 0:
                logger.info(f"Removed movie {movie_id} from favorites for user {user_id}")
                return True # Successfully removed
            else:
                logger.warning(f"Attempted to remove non-existent favorite movie {movie_id} for user {user_id}")
                return False # Not found
    except Exception as e:
        logger.error(f"Error removing favorite movie {movie_id} for user {user_id}: {e}")
        return None # Indicate error

async def add_user_if_not_exists(user_id: int, first_name: str | None, last_name: str | None, username: str | None):
    """Adds a user to the database if they don't already exist."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT OR IGNORE INTO users (user_id, first_name, last_name, username) VALUES (?, ?, ?, ?)",
                (user_id, first_name, last_name, username)
            )
            await db.commit()
    except Exception as e:
        logger.error(f"Error adding or ignoring user {user_id}: {e}")

# --- Admin Specific Functions ---

async def get_user_count() -> int:
    """Gets the total number of users in the database."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT COUNT(*) FROM users") as cursor:
                result = await cursor.fetchone()
                return result[0] if result else 0
    except Exception as e:
        logger.error(f"Error getting user count: {e}")
        return 0

async def get_total_favorites_count() -> int:
    """Gets the total number of favorite entries across all users."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT COUNT(*) FROM favorites") as cursor:
                result = await cursor.fetchone()
                return result[0] if result else 0
    except Exception as e:
        logger.error(f"Error getting total favorites count: {e}")
        return 0

async def get_all_user_ids() -> list[int]:
    """Gets all user IDs from the database."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT user_id FROM users") as cursor:
                rows = await cursor.fetchall()
                return [row[0] for row in rows]
    except Exception as e:
        logger.error(f"Error getting all user IDs: {e}")
        return []


