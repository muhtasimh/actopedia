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


async def get_movie_cast(movie_id: int):
    url = f"{BASE_URL}/movie/{movie_id}/credits"

    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            headers=headers
        )

        response.raise_for_status()

    return response.json()["cast"]


async def get_movie_details(movie_id: int):
    """
    Get information used by the recommendation algorithm.

    append_to_response=credits lets us retrieve the movie details
    and crew information with one TMDB request.
    """

    url = f"{BASE_URL}/movie/{movie_id}"

    params = {
        "language": "en-US",
        "append_to_response": "credits"
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            headers=headers,
            params=params
        )

        response.raise_for_status()

    data = response.json()

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