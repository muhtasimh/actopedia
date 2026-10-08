import asyncio
import os

import httpx
from dotenv import load_dotenv
from app.cache import get_json

load_dotenv()

BASE_URL = "https://api.themoviedb.org/3"
TMDB_TOKEN = os.getenv("TMDB_TOKEN")

_client = None
_request_limit = asyncio.Semaphore(40)

headers = {
    "Authorization": f"Bearer {TMDB_TOKEN}",
    "accept": "application/json"
}



def get_http_client():
    """Reuse TCP/TLS connections across TMDB requests."""
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=20,
            limits=httpx.Limits(max_connections=50, max_keepalive_connections=40),
        )
    return _client


async def close_http_client():
    """Release pooled connections during application shutdown."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def _tmdb_get(path, params=None):
    async def fetch():
        async with _request_limit:
            response = await get_http_client().get(
                f"{BASE_URL}{path}", headers=headers, params=params
            )
            response.raise_for_status()
            return response.json()

    return await get_json(path, params, fetch)


async def search_actors(query: str):

    params = {
        "query": query,
        "include_adult": "false",
        "language": "en-US",
        "page": 1
    }

    data = await _tmdb_get("/search/person", params)
    return data["results"]


async def get_actor_movies(actor_id: int):

    params = {
        "language": "en-US"
    }

    data = await _tmdb_get(f"/person/{actor_id}/movie_credits", params)
    return data["cast"]


async def get_movie_cast(movie_id: int):

    data = await _tmdb_get(f"/movie/{movie_id}/credits")
    return data["cast"]


async def get_movie_details(movie_id: int):
    """
    Get information used by the recommendation algorithm.

    append_to_response=credits lets us retrieve the movie details
    and crew information with one TMDB request.
    """


    params = {
        "language": "en-US",
        "append_to_response": "credits"
    }

    data = await _tmdb_get(f"/movie/{movie_id}", params)

    directors = [
        {
            "id": person["id"],
            "name": person["name"]
        }
        for person in data.get("credits", {}).get("crew", [])
        if person.get("job") == "Director"
    ]

    genres = [
        {
            "id": genre["id"],
            "name": genre["name"]
        }
        for genre in data.get("genres", [])
    ]

    return {
        "id": data["id"],
        "title": data.get("title"),
        "overview": data.get("overview") or "",
        "genres": genres,
        "directors": directors,
        "release_date": data.get("release_date"),
        "poster_path": data.get("poster_path"),
        "vote_average": data.get("vote_average") or 0,
        "vote_count": data.get("vote_count") or 0,
        "popularity": data.get("popularity") or 0
    }