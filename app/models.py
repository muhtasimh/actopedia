from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey
from app.database import Base


class Actor(Base):
    __tablename__ = "actors"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    popularity = Column(Float)


class Movie(Base):
    __tablename__ = "movies"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    release_date = Column(Date)
    vote_average = Column(Float)
    vote_count = Column(Integer)
    popularity = Column(Float)


class Credit(Base):
    __tablename__ = "credits"

    actor_id = Column(
        Integer,
        ForeignKey("actors.id"),
        primary_key=True
    )

    movie_id = Column(
        Integer,
        ForeignKey("movies.id"),
        primary_key=True
    )

    character = Column(String)