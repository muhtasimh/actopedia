from datetime import datetime

from app.database import SessionLocal
from app.models import Actor, Movie, Credit


def save_actor(actor_data):
    db = SessionLocal()

    try:
        actor = db.get(Actor, actor_data["id"])

        if actor is None:
            actor = Actor(
                id=actor_data["id"],
                name=actor_data["name"],
                popularity=actor_data.get("popularity")
            )
            db.add(actor)

        db.commit()
        return actor

    finally:
        db.close()

def save_movie(movie_data):
    db = SessionLocal()

    try:
        movie = db.get(Movie, movie_data["id"])

        if movie is None:
            release_date = None

            if movie_data.get("release_date"):
                release_date = datetime.strptime(
                    movie_data["release_date"],
                    "%Y-%m-%d"
                ).date()

            movie = Movie(
                id=movie_data["id"],
                title=movie_data["title"],
                release_date=release_date,
                vote_average=movie_data.get("vote_average"),
                vote_count=movie_data.get("vote_count"),
                popularity=movie_data.get("popularity")
            )

            db.add(movie)

        db.commit()
        return movie

    finally:
        db.close()


def save_credit(actor_id, movie_id, character):
    db = SessionLocal()

    try:
        credit = db.get(Credit, (actor_id, movie_id))

        if credit is None:
            credit = Credit(
                actor_id=actor_id,
                movie_id=movie_id,
                character=character
            )

            db.add(credit)

        db.commit()
        return credit

    finally:
        db.close()