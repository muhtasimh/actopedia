from fastapi import FastAPI, Query

from app.tmdb import search_actors, get_actor_movies

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