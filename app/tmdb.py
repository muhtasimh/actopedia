import os

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.themoviedb.org/3"
TMDB_TOKEN = os.getenv("TMDB_TOKEN")

headers = {
    "Authorization": f"Bearer {TMDB_TOKEN}",
    "accept": "application/json"
}


async def search_actors(query: str):
    url = f"{BASE_URL}/search/person"

    params = {
        "query": query,
        "include_adult": "false",
        "language": "en-US",
        "page": 1
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            headers=headers,
            params=params
        )

        response.raise_for_status()

    return response.json()["results"]

async def get_actor_movies(actor_id: int):
    url = f"{BASE_URL}/person/{actor_id}/movie_credits"

    params = {
        "language": "en-US"
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            headers=headers,
            params=params
        )

        response.raise_for_status()

    return response.json()["cast"]