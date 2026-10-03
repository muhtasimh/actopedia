# Actopedia

Actopedia is a full-stack movie discovery application that recommends movies based on the filmographies and professional connections of 2–5 selected actors or actresses.

Rather than ranking movies primarily by popularity or ratings, Actopedia builds profiles of the selected stars and explores their wider collaboration networks to generate a personalized Top 10 using a custom Match Score.

## Live Demo

[Open Actopedia](https://actopediafrontend.z9.web.core.windows.net/)

The application is deployed on Microsoft Azure, with the React frontend hosted through Azure Storage and the FastAPI backend and PostgreSQL database running on Azure services.

## Features

- Search for actors and actresses using The Movie Database (TMDB)
- Select between 2 and 5 stars
- Explore movies through shared casts and collaboration networks
- Build actor/actress profiles using movies from across their careers
- Compare candidate movies by genre, plot descriptions, directors, and professional connections
- Generate a ranked Top 10 with a custom Match Score
- Display movie posters, release years, TMDB ratings, and Match Scores
- Persist actor, movie, and credit data in PostgreSQL
- Automated backend testing with Pytest
- Dockerized backend
- Continuous integration with GitHub Actions

## Tech Stack

### Frontend
- React
- Vite
- JavaScript
- CSS

### Backend
- Python
- FastAPI
- SQLAlchemy
- PostgreSQL
- HTTPX

### API
- The Movie Database (TMDB) API

### Testing and DevOps
- Pytest
- Docker
- GitHub Actions

## How Recommendations Work

Actopedia combines film content with professional collaboration data rather than relying on a single similarity metric.

### 1. Build Star Profiles

For each selected actor or actress, Actopedia creates a representative film profile using movies from across their career.

The filmography is divided into early, middle, and later periods, and representative movies are selected from each period. This prevents the profile from being based entirely on a star's most recent or most popular work.

These movies are used to build profiles containing:

- Genres
- Movie descriptions
- Directors
- Collaboration history

### 2. Explore Collaboration Networks

Actopedia examines casts from the selected stars' movies to identify collaborators.

Those collaborators connect the selected stars to additional filmographies, creating a larger candidate pool of potentially relevant movies.

Repeated collaborations create stronger network connections.

### 3. Content-Aware Candidate Selection

The collaboration graph can produce thousands of potential movies.

Before retrieving detailed information for every candidate, Actopedia performs a lightweight comparison using information already available from TMDB, including:

- Direct casting overlap
- Genre overlap
- Plot-description similarity
- Collaboration-network connections

The strongest candidates move to the final ranking stage.

This reduces unnecessary API requests while allowing the recommendation engine to explore a much larger movie network.

### 4. Calculate the Match Score

The remaining candidates receive a Match Score out of 100 using five weighted signals:

| Signal | Weight | Description |
|---|---:|---|
| Direct Casting Match | 30% | Measures how many of the selected stars appear directly in the movie |
| Genre Profile | 25% | Measures how closely the movie's genres match the combined film profiles |
| Plot Description Similarity | 20% | Compares words in movie descriptions with descriptions from the selected stars' profile movies |
| Director Connection | 15% | Measures connections to directors appearing across the selected stars' filmographies |
| Collaboration Network | 10% | Measures indirect connections through collaborators and repeated professional relationships |

The 10 highest-scoring movies are returned as the final recommendations.

TMDB ratings, vote counts, and popularity do not directly contribute to the final Match Score.

## Plot Description Similarity

Plot similarity is calculated using a lightweight text-comparison approach.

Movie descriptions are normalized and tokenized, common words are removed, and the resulting word sets are compared using Jaccard similarity:

`similarity = shared words / total unique words`

A candidate movie is compared with descriptions from the selected stars' profile movies, allowing plot information to influence recommendations without requiring a machine-learning model or external AI service.

## Architecture

```text
React Frontend
      |
      | HTTP
      v
FastAPI Backend
      |
      +-------------------+
      |                   |
      v                   v
PostgreSQL          TMDB API
      |
      v
Actors / Movies / Credits
```

The React frontend handles star selection and recommendation presentation.

FastAPI provides the application API and recommendation engine. SQLAlchemy manages persisted actor, movie, and credit data in PostgreSQL, while TMDB supplies external movie metadata.

## API Endpoints

### Search for stars

```http
GET /actors/search?q={name}
```

Searches TMDB for actors and actresses matching the supplied name.

### Generate recommendations

```http
GET /actors/recommendations?ids={id1},{id2}
```

Accepts between 2 and 5 TMDB person IDs and returns the Top 10 ranked movie recommendations.

Example:

```http
GET /actors/recommendations?ids=6193,10297
```

## Running Locally

### 1. Clone the repository

```bash
git clone https://github.com/muhtasimh/actopedia.git
cd actopedia
```

### 2. Create a Python virtual environment

Windows:

```bash
py -m venv .venv
.venv\Scripts\activate
```

### 3. Install backend dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root and provide the required configuration:

```env
TMDB_TOKEN=your_tmdb_api_token
DATABASE_URL=your_postgresql_connection_string
```

### 5. Start the backend

```bash
uvicorn app.main:app --reload
```

The API will run at:

```text
http://127.0.0.1:8000
```

Interactive FastAPI documentation is available at:

```text
http://127.0.0.1:8000/docs
```

### 6. Start the frontend

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at:

```text
http://localhost:5173
```

## Testing

Run the backend test suite from the project root:

```bash
py -m pytest -v
```

GitHub Actions automatically runs the backend tests on pushes and pull requests.

## Docker

Build the backend image:

```bash
docker build -t actopedia .
```

Run the container with the required environment variables:

```bash
docker run -p 8000:8000 --env-file .env actopedia
```

## Project Structure

```text
Actopedia/
├── .github/
│   └── workflows/
├── app/
│   ├── __init__.py
│   ├── crud.py
│   ├── database.py
│   ├── main.py
│   ├── models.py
│   └── tmdb.py
├── frontend/
│   ├── public/
│   └── src/
│       ├── App.css
│       ├── App.jsx
│       ├── index.css
│       └── main.jsx
├── tests/
│   └── test_api.py
├── Dockerfile
├── requirements.txt
└── README.md
```

## Data Source

Movie, cast, genre, director, rating, popularity, and image data are provided through The Movie Database (TMDB) API.