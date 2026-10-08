import asyncio
import logging
import time
import re

from collections import Counter, defaultdict

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from app.tmdb import (
    search_actors,
    get_actor_movies,
    get_movie_cast,
    get_movie_details
)

from app.crud import save_actor, save_movie, save_credit


logger = logging.getLogger("uvicorn.error")

app = FastAPI(
    title="Actopedia",
    description="Actor discovery and movie matching engine",
    version="0.5.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "http://localhost:5173",
    "http://localhost:5174",
    "https://actopediafrontend.z9.web.core.windows.net",
],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "but",
    "by", "for", "from", "has", "have", "he", "her", "his",
    "in", "into", "is", "it", "its", "of", "on", "or", "she",
    "that", "the", "their", "them", "they", "this", "to", "was",
    "were", "when", "where", "who", "with", "after", "before",
    "while", "during", "must", "him", "herself", "himself",
    "up", "out", "over", "under", "through", "against", "about",
    "new", "one"
}


def tokenize(text):
    words = re.findall(r"[a-zA-Z]+", (text or "").lower())

    return {
        word
        for word in words
        if len(word) >= 4 and word not in STOP_WORDS
    }


def jaccard_similarity(first, second):
    if not first or not second:
        return 0

    union = first | second

    if not union:
        return 0

    return len(first & second) / len(union)


def movie_year(movie):
    release_date = movie.get("release_date") or ""

    try:
        return int(release_date[:4])
    except (ValueError, TypeError):
        return None


def choose_profile_movies(movies, limit=15):
    """
    Build a broader actor profile instead of simply using
    the actor's most popular movies.

    Movies are divided into career periods. Strong credits
    from each period are selected so that one part of an
    actor's career does not define the entire profile.
    """

    valid_movies = [
        movie
        for movie in movies
        if movie_year(movie) is not None
    ]

    if len(valid_movies) <= limit:
        return valid_movies

    valid_movies.sort(
        key=lambda movie: movie_year(movie)
    )

    # Divide the actor's career into three roughly
    # equal periods: earlier, middle and later.
    section_size = max(
        len(valid_movies) // 3,
        1
    )

    early = valid_movies[:section_size]

    middle = valid_movies[
        section_size:section_size * 2
    ]

    later = valid_movies[
        section_size * 2:
    ]

    selected = []

    for section in [early, middle, later]:

        section.sort(
            key=lambda movie: (
                movie.get("popularity") or 0
            ),
            reverse=True
        )

        selected.extend(section[:5])

    # Remove accidental duplicates.
    unique = {}

    for movie in selected:
        unique[movie["id"]] = movie

    return list(unique.values())[:limit]


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
        actor_data = {
            "id": person["id"],
            "name": person["name"],
            "known_for_department": person.get("known_for_department"),
            "profile_path": person.get("profile_path"),
            "popularity": person.get("popularity")
        }

        actors.append(actor_data)
        save_actor(actor_data)

    return {
        "query": q,
        "results": actors
    }


@app.get("/actors/{actor_id}/movies")
async def actor_movies(actor_id: int):
    results = await get_actor_movies(actor_id)

    movies = []

    for movie in results:
        movie_data = {
            "id": movie["id"],
            "title": movie["title"],
            "release_date": movie.get("release_date"),
            "poster_path": movie.get("poster_path"),
            "character": movie.get("character"),
            "vote_average": movie.get("vote_average"),
            "vote_count": movie.get("vote_count"),
            "popularity": movie.get("popularity")
        }

        movies.append(movie_data)

        save_movie(movie_data)

        save_credit(
            actor_id,
            movie["id"],
            movie.get("character")
        )

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
    actor_ids = [
        int(actor_id.strip())
        for actor_id in ids.split(",")
        if actor_id.strip()
    ]

    actor_ids = list(dict.fromkeys(actor_ids))

    if len(actor_ids) < 2:
        return {
            "error": "Please provide at least two actor IDs."
        }

    if len(actor_ids) > 5:
        return {
            "error": "Please provide no more than five actor IDs."
        }

    started = time.perf_counter()
    stage_started = started

    def log_stage(stage, **counts):
        nonlocal stage_started
        now = time.perf_counter()
        logger.info("recommendations stage=%s elapsed=%.2fs total=%.2fs counts=%s", stage, now - stage_started, now - started, counts)
        stage_started = now

    # --------------------------------------------------
    # 1. Load selected actor filmographies
    # --------------------------------------------------

    filmographies = await asyncio.gather(
        *(get_actor_movies(actor_id) for actor_id in actor_ids)
    )

    log_stage("selected_filmographies", actors=len(actor_ids))

    selected_movie_actors = defaultdict(set)
    selected_movies = {}

    for actor_id, movies in zip(actor_ids, filmographies):

        for movie in movies:
            movie_id = movie["id"]

            selected_movie_actors[
                movie_id
            ].add(actor_id)

            if movie_id not in selected_movies:
                selected_movies[movie_id] = movie

    # --------------------------------------------------
    # 2. Build balanced actor profiles
    # --------------------------------------------------

    profile_movies = []
    profile_movie_ids = set()

    for movies in filmographies:

        chosen_movies = choose_profile_movies(
            movies,
            limit=15
        )

        profile_movies.extend(chosen_movies)

        for movie in chosen_movies:
            profile_movie_ids.add(movie["id"])

    # --------------------------------------------------
    # 3. Build CHEAP profile information
    #
    # Actor movie-credit results already contain
    # genre_ids and overview, so we can use these without
    # making additional TMDB requests.
    # --------------------------------------------------

    cheap_genre_counts = Counter()
    cheap_profile_overviews = []

    for movie in profile_movies:

        for genre_id in movie.get(
            "genre_ids",
            []
        ):
            cheap_genre_counts[genre_id] += 1

        words = tokenize(
            movie.get("overview", "")
        )

        if words:
            cheap_profile_overviews.append(
                words
            )

    max_cheap_genre_count = max(
        cheap_genre_counts.values(),
        default=1
    )

    # --------------------------------------------------
    # 4. Load rich profile details
    #
    # Needed mainly for director information and final
    # profile scoring.
    # --------------------------------------------------

    profile_details = await asyncio.gather(
        *(
            get_movie_details(movie_id)
            for movie_id in profile_movie_ids
        )
    )

    log_stage("profile_details", movies=len(profile_movie_ids))

    genre_counts = Counter()
    director_counts = Counter()
    profile_overviews = []

    for movie in profile_details:

        for genre in movie["genres"]:
            genre_counts[
                genre["id"]
            ] += 1

        for director in movie["directors"]:
            director_counts[
                director["id"]
            ] += 1

        words = tokenize(
            movie["overview"]
        )

        if words:
            profile_overviews.append(
                words
            )

    max_genre_count = max(
        genre_counts.values(),
        default=1
    )

    max_director_count = max(
        director_counts.values(),
        default=1
    )

    # --------------------------------------------------
    # 5. Find collaborators
    # --------------------------------------------------

    collaborator_connections = defaultdict(
        lambda: defaultdict(int)
    )

    for actor_id, movies in zip(
        actor_ids,
        filmographies
    ):

        # We can still use popular films here because
        # this step is only discovering collaborators,
        # not assigning recommendation points.
        exploration_movies = sorted(
            movies,
            key=lambda movie: (
                movie.get("popularity") or 0
            ),
            reverse=True
        )[:8]

        casts = await asyncio.gather(
            *(
                get_movie_cast(movie["id"])
                for movie in exploration_movies
            )
        )

        for cast in casts:

            for person in cast[:15]:

                collaborator_id = person["id"]

                if collaborator_id not in actor_ids:

                    collaborator_connections[
                        collaborator_id
                    ][actor_id] += 1

    log_stage("collaborator_casts", collaborators=len(collaborator_connections))

    # --------------------------------------------------
    # 6. Load collaborator filmographies
    # --------------------------------------------------

    collaborator_ids = list(
        collaborator_connections.keys()
    )

    collaborator_filmographies = await asyncio.gather(
        *(
            get_actor_movies(collaborator_id)
            for collaborator_id in collaborator_ids
        )
    )

    log_stage("collaborator_filmographies", collaborators=len(collaborator_ids))

    # --------------------------------------------------
    # 7. Build candidate pool
    # --------------------------------------------------

    candidate_movies = {}

    # Direct shared movies.
    for movie_id, connected_actors in (
        selected_movie_actors.items()
    ):

        if len(connected_actors) < 2:
            continue

        movie = selected_movies[movie_id]

        candidate_movies[movie_id] = {
            "id": movie_id,
            "title": movie.get(
                "title",
                "Unknown"
            ),
            "release_date": movie.get(
                "release_date"
            ),
            "poster_path": movie.get(
                "poster_path"
            ),
            "vote_average": movie.get(
                "vote_average"
            ) or 0,
            "vote_count": movie.get(
                "vote_count"
            ) or 0,
            "popularity": movie.get(
                "popularity"
            ) or 0,

            "genre_ids": movie.get(
                "genre_ids",
                []
            ),

            "overview": movie.get(
                "overview",
                ""
            ),

            "direct_actor_ids": set(
                connected_actors
            ),

            "connected_actor_ids": set(
                connected_actors
            ),

            "collaboration_strength": defaultdict(
                int
            ),

            "graph_paths": 0,
            "is_shared_movie": True
        }

    # Indirect discovery candidates.
    for collaborator_id, movies in zip(
        collaborator_ids,
        collaborator_filmographies
    ):

        connection_counts = (
            collaborator_connections[
                collaborator_id
            ]
        )

        for movie in movies:

            movie_id = movie["id"]

            # Exclude films containing only one of the
            # selected actors.
            if movie_id in selected_movie_actors:

                if len(
                    selected_movie_actors[
                        movie_id
                    ]
                ) < 2:
                    continue

            if movie_id not in candidate_movies:

                candidate_movies[movie_id] = {
                    "id": movie_id,
                    "title": movie.get(
                        "title",
                        "Unknown"
                    ),
                    "release_date": movie.get(
                        "release_date"
                    ),
                    "poster_path": movie.get(
                        "poster_path"
                    ),
                    "vote_average": movie.get(
                        "vote_average"
                    ) or 0,
                    "vote_count": movie.get(
                        "vote_count"
                    ) or 0,
                    "popularity": movie.get(
                        "popularity"
                    ) or 0,

                    "genre_ids": movie.get(
                        "genre_ids",
                        []
                    ),

                    "overview": movie.get(
                        "overview",
                        ""
                    ),

                    "direct_actor_ids": set(),

                    "connected_actor_ids": set(),

                    "collaboration_strength": defaultdict(
                        int
                    ),

                    "graph_paths": 0,

                    "is_shared_movie": False
                }

            candidate = candidate_movies[
                movie_id
            ]

            candidate[
                "graph_paths"
            ] += 1

            for (
                actor_id,
                count
            ) in connection_counts.items():

                candidate[
                    "connected_actor_ids"
                ].add(actor_id)

                candidate[
                    "collaboration_strength"
                ][actor_id] += count

    # --------------------------------------------------
    # 8. CONTENT-AWARE PRESELECTION
    #
    # Instead of selecting the 75 candidates based only
    # on the actor graph, use:
    #
    # collaboration network
    # genre profile
    # description similarity
    #
    # This is deliberately inexpensive because all of
    # this information came with movie-credit requests.
    # --------------------------------------------------

    def preselection_score(movie):

        # ----------------------------
        # Direct actor connection
        # ----------------------------

        direct_coverage = (
            len(movie["direct_actor_ids"])
            / len(actor_ids)
        )

        # ----------------------------
        # Collaboration network
        # ----------------------------

        network_ids = (
            movie["direct_actor_ids"]
            | movie["connected_actor_ids"]
        )

        network_coverage = (
            len(network_ids)
            / len(actor_ids)
        )

        collaboration_total = sum(
            movie[
                "collaboration_strength"
            ].values()
        )

        recurring_strength = min(
            collaboration_total / 6,
            1
        )

        network_component = (
            network_coverage * 0.6
            + recurring_strength * 0.4
        )

        # ----------------------------
        # Genre similarity
        # ----------------------------

        candidate_genres = set(
            movie.get(
                "genre_ids",
                []
            )
        )

        if candidate_genres:

            genre_weights = [
                cheap_genre_counts.get(
                    genre_id,
                    0
                ) / max_cheap_genre_count
                for genre_id in candidate_genres
            ]

            genre_component = (
                sum(genre_weights)
                / len(candidate_genres)
            )

        else:
            genre_component = 0

        # ----------------------------
        # Description similarity
        # ----------------------------

        candidate_words = tokenize(
            movie.get(
                "overview",
                ""
            )
        )

        similarities = sorted(
            (
                jaccard_similarity(
                    candidate_words,
                    profile_words
                )
                for profile_words
                in cheap_profile_overviews
            ),
            reverse=True
        )

        strongest = similarities[:3]

        if strongest:

            raw_description = (
                sum(strongest)
                / len(strongest)
            )

            description_component = min(
                raw_description * 4,
                1
            )

        else:
            description_component = 0

        # Preselection is NOT the final Match Score.
        #
        # Direct overlap is kept very strong so shared
        # movies cannot accidentally disappear.
        #
        # Everything else balances relationship and
        # content relevance.
        return (
            direct_coverage * 0.30
            + network_component * 0.25
            + genre_component * 0.25
            + description_component * 0.20
        )

    candidate_list = list(
        candidate_movies.values()
    )

    candidate_list.sort(
        key=preselection_score,
        reverse=True
    )

    enrichment_candidates = (
        candidate_list[:75]
    )

    # --------------------------------------------------
    # 9. Load rich details for the 75 finalists
    # --------------------------------------------------

    candidate_details = await asyncio.gather(
        *(
            get_movie_details(movie["id"])
            for movie in enrichment_candidates
        )
    )

    details_by_id = {
        movie["id"]: movie
        for movie in candidate_details
    }

    log_stage("finalist_details", finalists=len(enrichment_candidates), candidates=len(candidate_movies))

    # --------------------------------------------------
    # 10. FINAL MATCH SCORE
    #
    # Direct actor match       30
    # Genre profile            25
    # Story/theme similarity   20
    # Director connection      15
    # Collaboration network    10
    #
    # Total                   100
    #
    # Rating, popularity and vote count = 0 points.
    # --------------------------------------------------

    recommendations = []

    for movie in enrichment_candidates:

        details = details_by_id.get(
            movie["id"]
        )

        if not details:
            continue

        # ----------------------------
        # Direct actor match — 30
        # ----------------------------

        direct_actor_count = len(
            movie["direct_actor_ids"]
        )

        direct_coverage = (
            direct_actor_count
            / len(actor_ids)
        )

        direct_score = (
            direct_coverage * 30
        )

        # ----------------------------
        # Genre profile — 25
        # ----------------------------

        candidate_genres = {
            genre["id"]
            for genre in details["genres"]
        }

        if candidate_genres:

            genre_weights = [
                genre_counts.get(
                    genre_id,
                    0
                ) / max_genre_count
                for genre_id in candidate_genres
            ]

            genre_similarity = (
                sum(genre_weights)
                / len(candidate_genres)
            )

        else:
            genre_similarity = 0

        genre_score = (
            genre_similarity * 25
        )

        # ----------------------------
        # Story/theme — 20
        # ----------------------------

        candidate_words = tokenize(
            details["overview"]
        )

        description_matches = sorted(
            (
                jaccard_similarity(
                    candidate_words,
                    profile_words
                )
                for profile_words
                in profile_overviews
            ),
            reverse=True
        )

        strongest_matches = (
            description_matches[:3]
        )

        if strongest_matches:

            raw_description_similarity = (
                sum(strongest_matches)
                / len(strongest_matches)
            )

        else:
            raw_description_similarity = 0

        description_similarity = min(
            raw_description_similarity * 4,
            1
        )

        description_score = (
            description_similarity * 20
        )

        # ----------------------------
        # Director connection — 15
        # ----------------------------

        candidate_directors = {
            director["id"]
            for director
            in details["directors"]
        }

        if candidate_directors:

            director_weights = [
                director_counts.get(
                    director_id,
                    0
                ) / max_director_count
                for director_id
                in candidate_directors
            ]

            director_similarity = max(
                director_weights,
                default=0
            )

        else:
            director_similarity = 0

        director_score = (
            director_similarity * 15
        )

        # ----------------------------
        # Collaboration network — 10
        # ----------------------------

        connected_actor_ids = (
            movie["connected_actor_ids"]
        )

        network_coverage = (
            len(connected_actor_ids)
            / len(actor_ids)
        )

        collaboration_values = []

        for actor_id in actor_ids:

            count = movie[
                "collaboration_strength"
            ].get(actor_id, 0)

            actor_strength = min(
                count / 3,
                1
            )

            collaboration_values.append(
                actor_strength
            )

        recurring_strength = (
            sum(collaboration_values)
            / len(actor_ids)
        )

        network_similarity = (
            network_coverage * 0.5
            + recurring_strength * 0.5
        )

        network_score = (
            network_similarity * 10
        )

        # ----------------------------
        # Final total
        # ----------------------------

        score = (
            direct_score
            + genre_score
            + description_score
            + director_score
            + network_score
        )

        recommendations.append({
            "id": movie["id"],
            "title": movie["title"],
            "release_date": movie["release_date"],
            "poster_path": movie.get(
                "poster_path"
            ),

            # Display only
            "vote_average": movie[
                "vote_average"
            ],
            "vote_count": movie[
                "vote_count"
            ],
            "popularity": movie[
                "popularity"
            ],

            # Explanation
            "genres": [
                genre["name"]
                for genre
                in details["genres"]
            ],

            "directors": [
                director["name"]
                for director
                in details["directors"]
            ],

            "direct_actor_count": (
                direct_actor_count
            ),

            "connected_actor_count": len(
                connected_actor_ids
            ),

            "graph_paths": movie[
                "graph_paths"
            ],

            "is_shared_movie": movie[
                "is_shared_movie"
            ],

            # Score breakdown
            "direct_actor_score": round(
                direct_score,
                2
            ),

            "genre_score": round(
                genre_score,
                2
            ),

            "description_score": round(
                description_score,
                2
            ),

            "director_score": round(
                director_score,
                2
            ),

            "network_score": round(
                network_score,
                2
            ),

            "score": round(
                score,
                2
            )
        })

    # --------------------------------------------------
    # 11. Return Top 10
    # --------------------------------------------------

    recommendations.sort(
        key=lambda movie: (
            movie["score"],
            movie["direct_actor_count"],
            movie["connected_actor_count"]
        ),
        reverse=True
    )

    log_stage("scoring", recommendations=len(recommendations))

    return {
        "actor_ids": actor_ids,
        "candidate_count": len(
            candidate_movies
        ),
        "enriched_candidate_count": len(
            enrichment_candidates
        ),
        "recommendations": recommendations[:10]
    }