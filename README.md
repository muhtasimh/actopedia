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


## Plot Description Similarity

Plot similarity is calculated using a lightweight text-comparison approach.

Movie descriptions are normalized and tokenized, common words are removed, and the resulting word sets are compared using Jaccard similarity:

similarity = shared words / total unique words

A candidate movie is compared with descriptions from the selected stars' profile movies, allowing plot information to influence recommendations without requiring a machine-learning model or external AI service.
