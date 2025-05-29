# -*- coding: utf-8 -*-
import aiohttp
import logging
from typing import List, Dict, Optional, Any

# Use absolute import
from src.config import TMDB_API_KEY

BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500" # Base URL for posters

logger = logging.getLogger(__name__)

async def _make_request(session: aiohttp.ClientSession, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Helper function to make asynchronous requests to TMDb API."""
    if params is None:
        params = {}
    params["api_key"] = TMDB_API_KEY
    params["language"] = "ar-SA" # Request Arabic language content

    # Ensure boolean parameters are passed as strings if required by API
    processed_params = params.copy()
    for key, value in processed_params.items():
        if isinstance(value, bool):
            processed_params[key] = str(value).lower() # Convert True -> "true", False -> "false"

    url = f"{BASE_URL}{endpoint}"
    try:
        logger.debug(f"Making TMDb API request to: {url} with params: {processed_params}")
        async with session.get(url, params=processed_params) as response:
            logger.debug(f"TMDb API response status: {response.status}")
            response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
            data = await response.json()
            logger.debug(f"TMDb API request to {url} successful.")
            return data
    except aiohttp.ClientResponseError as e:
        logger.error(f"Error fetching data from TMDb API ({url}) - Status: {e.status}, Message: {e.message}, Headers: {e.headers}")
        try:
            error_body = await e.text()
            logger.error(f"TMDb API error response body: {error_body}")
        except Exception as read_err:
            logger.error(f"Could not read error response body: {read_err}")
        return None
    except aiohttp.ClientError as e:
        logger.error(f"Client error during TMDb API request ({url}): {e}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred during TMDb API request ({url}): {e}", exc_info=True)
        return None

async def get_genres(session: aiohttp.ClientSession) -> Optional[Dict[int, str]]:
    """Fetches movie genres from TMDb."""
    endpoint = "/genre/movie/list"
    data = await _make_request(session, endpoint)
    if data and "genres" in data:
        return {genre["id"]: genre["name"] for genre in data["genres"]}
    return None

async def discover_movies_by_genre(session: aiohttp.ClientSession, genre_id: int, page: int = 1) -> Optional[List[Dict[str, Any]]]:
    """Discovers movies based on genre ID."""
    endpoint = "/discover/movie"
    params = {
        "with_genres": genre_id,
        "sort_by": "popularity.desc",
        "include_adult": "false", # Pass as string "false"
        "page": page
    }
    data = await _make_request(session, endpoint, params)
    if data and "results" in data:
        return data["results"]
    return None

async def search_movies(session: aiohttp.ClientSession, query: str, page: int = 1) -> Optional[List[Dict[str, Any]]]:
    """Searches for movies based on a query string."""
    endpoint = "/search/movie"
    params = {
        "query": query,
        "include_adult": "false", # Pass as string "false"
        "page": page
    }
    data = await _make_request(session, endpoint, params)
    if data and "results" in data:
        return data["results"]
    return None

async def get_movie_details(session: aiohttp.ClientSession, movie_id: int) -> Optional[Dict[str, Any]]:
    """Fetches detailed information for a specific movie ID, including credits."""
    endpoint = f"/movie/{movie_id}"
    # Append recommendations and credits (cast/crew) to the response
    params = {"append_to_response": "recommendations,credits"}
    data = await _make_request(session, endpoint, params)
    return data # Return the full data dictionary or None if error

async def get_popular_movies(session: aiohttp.ClientSession, page: int = 1) -> Optional[List[Dict[str, Any]]]:
    """Fetches popular movies."""
    endpoint = "/movie/popular"
    params = {
        "page": page,
        "include_adult": "false" # Pass as string "false"
    }
    data = await _make_request(session, endpoint, params)
    if data and "results" in data:
        return data["results"]
    return None

def get_poster_url(poster_path: Optional[str]) -> Optional[str]:
    """Constructs the full URL for a movie poster."""
    if poster_path:
        return f"{IMAGE_BASE_URL}{poster_path}"
    return None

