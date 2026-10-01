import asyncio

from fastapi import FastAPI, Query

from app.tmdb import search_actors, get_actor_movies, get_movie_cast

app = FastAPI(
    title="Actopedia",
    description="Actor discovery and movie matching engine",
    version="0.1.0"
)


@app.get("/")
def home():
    return {
        "name": "Actopedia",
        "status": "running"
    }


@app.get("/actors/search")
async def actor_search(q: str = Query(min_length=1)):
    results = await search_actors(q)

    actors = []

    for person in results:
        actors.append({
            "id": person["id"],
            "name": person["name"],
            "known_for_department": person.get("known_for_department"),
            "profile_path": person.get("profile_path"),
            "popularity": person.get("popularity")
        })

    return {
        "query": q,
        "results": actors
    }


@app.get("/actors/{actor_id}/movies")
async def actor_movies(actor_id: int):
    results = await get_actor_movies(actor_id)

    movies = []

    for movie in results:
        movies.append({
            "id": movie["id"],
            "title": movie["title"],
            "release_date": movie.get("release_date"),
            "character": movie.get("character"),
            "vote_average": movie.get("vote_average"),
            "popularity": movie.get("popularity")
        })

    movies.sort(
        key=lambda movie: movie["popularity"] or 0,
        reverse=True
    )

    return {
        "actor_id": actor_id,
        "movies": movies
    }

@app.get("/actors/shared-movies")
async def shared_movies(ids: str = Query(..., description="Comma-separated actor IDs")):
    actor_ids = [int(actor_id.strip()) for actor_id in ids.split(",")]

    if len(actor_ids) < 2:
        return {
            "error": "Please provide at least two actor IDs."
        }

    filmographies = await asyncio.gather(
        *(get_actor_movies(actor_id) for actor_id in actor_ids)
    )

    movie_maps = []

    for movies in filmographies:
        movie_maps.append({
            movie["id"]: movie
            for movie in movies
        })

    shared_ids = set(movie_maps[0].keys())

    for movie_map in movie_maps[1:]:
        shared_ids &= set(movie_map.keys())

    shared = []

    for movie_id in shared_ids:
        movie = movie_maps[0][movie_id]

        shared.append({
            "id": movie["id"],
            "title": movie["title"],
            "release_date": movie.get("release_date"),
            "vote_average": movie.get("vote_average"),
            "popularity": movie.get("popularity")
        })

    shared.sort(
        key=lambda movie: movie["popularity"] or 0,
        reverse=True
    )

    return {
        "actor_ids": actor_ids,
        "shared_movies": shared,
        "count": len(shared)
    }

@app.get("/movies/{movie_id}/cast")
async def movie_cast(movie_id: int):
    results = await get_movie_cast(movie_id)

    cast = []

    for person in results[:20]:
        cast.append({
            "id": person["id"],
            "name": person["name"],
            "character": person.get("character"),
            "order": person.get("order")
        })

    return {
        "movie_id": movie_id,
        "cast": cast
    }