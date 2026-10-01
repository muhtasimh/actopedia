import asyncio

from collections import defaultdict

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

@app.get("/actors/recommendations")
async def actor_recommendations(
    ids: str = Query(..., description="Comma-separated actor IDs")
):
    actor_ids = [int(actor_id.strip()) for actor_id in ids.split(",")]

    if len(actor_ids) < 2:
        return {
            "error": "Please provide at least two actor IDs."
        }

    # --------------------------------------------------
    # 1. Get filmographies for selected actors
    # --------------------------------------------------

    filmographies = await asyncio.gather(
        *(get_actor_movies(actor_id) for actor_id in actor_ids)
    )

    searched_actor_movie_ids = {
        movie["id"]
        for filmography in filmographies
        for movie in filmography
    }

    # --------------------------------------------------
    # 2. Find collaborators
    # --------------------------------------------------

    collaborator_connections = defaultdict(set)

    for actor_id, movies in zip(actor_ids, filmographies):

        top_movies = sorted(
            movies,
            key=lambda movie: movie.get("popularity") or 0,
            reverse=True
        )[:5]

        casts = await asyncio.gather(
            *(get_movie_cast(movie["id"]) for movie in top_movies)
        )

        for cast in casts:
            for person in cast[:15]:

                co_star_id = person["id"]

                if co_star_id not in actor_ids:
                    collaborator_connections[co_star_id].add(actor_id)

    # --------------------------------------------------
    # 3. Get collaborator filmographies concurrently
    # --------------------------------------------------

    collaborator_ids = list(collaborator_connections.keys())

    collaborator_filmographies = await asyncio.gather(
        *(get_actor_movies(actor_id) for actor_id in collaborator_ids)
    )

    # --------------------------------------------------
    # 4. Build candidate movie pool
    # --------------------------------------------------

    candidate_movies = {}

    for collaborator_id, movies in zip(
        collaborator_ids,
        collaborator_filmographies
    ):
        connected_to = collaborator_connections[collaborator_id]

        for movie in movies:

            movie_id = movie["id"]

            # Don't recommend movies the searched actors
            # already appeared in
            if movie_id in searched_actor_movie_ids:
                continue

            if movie_id not in candidate_movies:
                candidate_movies[movie_id] = {
                    "id": movie_id,
                    "title": movie["title"],
                    "release_date": movie.get("release_date"),
                    "vote_average": movie.get("vote_average") or 0,
                    "vote_count": movie.get("vote_count") or 0,
                    "popularity": movie.get("popularity") or 0,
                    "graph_paths": 0,
                    "connected_actor_ids": set()
                }

            candidate_movies[movie_id]["graph_paths"] += 1

            candidate_movies[movie_id]["connected_actor_ids"].update(
                connected_to
            )

    # --------------------------------------------------
    # 5. Score candidates
    # --------------------------------------------------

    recommendations = []

    for movie in candidate_movies.values():

        rating = movie["vote_average"]
        vote_count = movie["vote_count"]
        popularity = movie["popularity"]
        graph_paths = movie["graph_paths"]

        connected_actor_count = len(
            movie["connected_actor_ids"]
        )

        # How many searched actors have a path to this movie?
        actor_coverage = (
            connected_actor_count / len(actor_ids)
        )

        # Score out of 100
        connection_score = actor_coverage * 30

        path_score = min(
            graph_paths / 5,
            1
        ) * 15

        rating_score = (
            rating / 10
        ) * 25

        reliability_score = min(
            vote_count / 1000,
            1
        ) * 15

        popularity_score = min(
            popularity / 50,
            1
        ) * 15

        score = (
            connection_score
            + path_score
            + rating_score
            + reliability_score
            + popularity_score
        )

        recommendations.append({
            "id": movie["id"],
            "title": movie["title"],
            "release_date": movie["release_date"],
            "vote_average": rating,
            "vote_count": vote_count,
            "popularity": popularity,
            "graph_paths": graph_paths,
            "connected_actor_count": connected_actor_count,
            "score": round(score, 2)
        })

    # --------------------------------------------------
    # 6. Rank and return Top 10
    # --------------------------------------------------

    recommendations.sort(
        key=lambda movie: movie["score"],
        reverse=True
    )

    return {
        "actor_ids": actor_ids,
        "candidate_count": len(candidate_movies),
        "recommendations": recommendations[:10]
    }