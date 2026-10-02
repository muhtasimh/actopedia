from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.main import app


client = TestClient(app)


def test_home():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "name": "Actopedia",
        "status": "running"
    }


@patch("app.main.save_actor")
@patch("app.main.search_actors", new_callable=AsyncMock)
def test_actor_search(mock_search, mock_save):
    mock_search.return_value = [
        {
            "id": 6193,
            "name": "Leonardo DiCaprio",
            "known_for_department": "Acting",
            "profile_path": "/test.jpg",
            "popularity": 8.1
        }
    ]

    response = client.get(
        "/actors/search",
        params={"q": "Leonardo DiCaprio"}
    )

    assert response.status_code == 200

    data = response.json()

    assert data["query"] == "Leonardo DiCaprio"
    assert len(data["results"]) == 1
    assert data["results"][0]["id"] == 6193
    assert data["results"][0]["name"] == "Leonardo DiCaprio"

    mock_save.assert_called_once()


@patch("app.main.save_credit")
@patch("app.main.save_movie")
@patch("app.main.get_actor_movies", new_callable=AsyncMock)
def test_actor_movies(mock_movies, mock_save_movie, mock_save_credit):
    mock_movies.return_value = [
        {
            "id": 597,
            "title": "Titanic",
            "release_date": "1997-12-19",
            "character": "Jack Dawson",
            "vote_average": 7.9,
            "vote_count": 25000,
            "popularity": 100.0
        }
    ]

    response = client.get("/actors/6193/movies")

    assert response.status_code == 200

    data = response.json()

    assert data["actor_id"] == 6193
    assert len(data["movies"]) == 1
    assert data["movies"][0]["title"] == "Titanic"

    mock_save_movie.assert_called_once()
    mock_save_credit.assert_called_once()


def test_recommendations_requires_two_actors():
    response = client.get(
        "/actors/recommendations",
        params={"ids": "6193"}
    )

    assert response.status_code == 200
    assert response.json() == {
        "error": "Please provide at least two actor IDs."
    }