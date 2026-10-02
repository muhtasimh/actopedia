# Actopedia

Actopedia is an actor discovery and movie matching API built with FastAPI. Users can search for actors, explore filmographies, find movies shared by multiple actors, and generate movie recommendations using a graph-based recommendation algorithm.

## Features

- Search actors using TMDB
- Retrieve actor filmographies
- Generate Top-10 movie recommendations from actor collaboration networks
- Persist actors, movies, and credits in PostgreSQL
- Automated API testing with pytest
- Dockerized application
- Continuous integration with GitHub Actions

## Tech Stack

- **Backend:** Python, FastAPI
- **Database:** PostgreSQL, SQLAlchemy
- **External API:** TMDB
- **Testing:** pytest, FastAPI TestClient
- **Containerization:** Docker
- **CI:** GitHub Actions

## Recommendation Algorithm

Actopedia builds a collaboration graph from the careers of selected actors.

For each selected actor, the algorithm:

1. Retrieves the actor's filmography.
2. Selects their 5 most popular movies.
3. Retrieves up to 15 cast members from each movie.
4. Uses those collaborators to discover additional films.
5. Removes movies already featuring the searched actors.
6. Scores and ranks the remaining candidates.

Candidate movies are ranked using five weighted signals:

| Signal | Weight |
| --- | ---: |
| Actor coverage | 30% |
| Collaboration graph paths | 15% |
| TMDB rating | 25% |
| Vote reliability | 15% |
| Popularity | 15% |

In a tested two-actor search, the algorithm evaluated **6,832 candidate movies** before returning the **Top 10 recommendations**.

## Database

Actopedia uses PostgreSQL to model the many-to-many relationship between actors and movies:

```text
Actor ──< Credit >── Movie
```

The database stores actor information, movie metadata, and actor/movie credits retrieved through the API.

## API Endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/` | API status |
| GET | `/actors/search?q=` | Search for actors |
| GET | `/actors/{actor_id}/movies` | Retrieve an actor's filmography |
| GET | `/actors/recommendations?ids=` | Generate movie recommendations |

Interactive API documentation is available through FastAPI Swagger UI at `/docs`.

## Running Locally

Create and activate a virtual environment, then install dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file containing:

```text
TMDB_TOKEN=your_tmdb_token
DATABASE_URL=your_postgresql_connection_string
```

Start the API:

```bash
uvicorn app.main:app --reload
```

Then open:

```text
http://127.0.0.1:8000/docs
```

## Tests

Run the automated test suite with:

```bash
python -m pytest -v
```

The tests mock external TMDB requests and database writes so the API can be tested independently of external services.

## Docker

Build the image:

```bash
docker build -t actopedia .
```

Run the container with environment variables supplied at runtime:

```bash
docker run --env-file .env -p 8000:8000 actopedia
```

## Continuous Integration

GitHub Actions automatically installs dependencies and runs the pytest suite on pushes and pull requests.

## Security

API tokens and database credentials are stored in environment variables and excluded from both Git and Docker images.