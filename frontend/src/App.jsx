import { useState } from "react";

import "./App.css";

const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";


function App() {

  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [selectedActors, setSelectedActors] = useState([]);
  const [loading, setLoading] = useState(false);
  const [recommendations, setRecommendations] = useState([]);
  const [recommendationLoading, setRecommendationLoading] = useState(false);


  async function searchActors() {

    if (!query.trim()) return;

    setLoading(true);

    try {

      const response = await fetch(
        `${API_URL}/actors/search?q=${encodeURIComponent(query)}`
      );

      const data = await response.json();

      setSearchResults(data.results || []);

    } catch (error) {

      console.error("Actor/actress search failed:", error);

    } finally {

      setLoading(false);

    }

  }


  function selectActor(actor) {

    if (selectedActors.some((selected) => selected.id === actor.id)) {
      return;
    }

    if (selectedActors.length >= 5) {
      return;
    }

    setSelectedActors([...selectedActors, actor]);

  }


  function removeActor(actorId) {

    setSelectedActors(
      selectedActors.filter((actor) => actor.id !== actorId)
    );

  }


  async function generateRecommendations() {

    if (selectedActors.length < 2) return;

    setRecommendationLoading(true);
    setRecommendations([]);

    const ids = selectedActors.map((actor) => actor.id).join(",");

    try {

      const response = await fetch(
        `${API_URL}/actors/recommendations?actor_ids=${ids}`
      );

      const data = await response.json();

      setRecommendations(data.recommendations || []);

    } catch (error) {

      console.error("Recommendation request failed:", error);

    } finally {

      setRecommendationLoading(false);

    }

  }


  return (

    <div className="app">

      <header>

        <h1>Actopedia</h1>

        <p>Discover movies through the stars you love.</p>

      </header>


      <main>

        <section className="how-it-works">

          <h2>How It Works</h2>

          <div className="steps">

            <div className="step-card">

              <span className="step-number">1</span>

              <h3>Pick Your Stars</h3>

              <p>
                Search for and select 2–5 actors/actresses you're interested in.
              </p>

            </div>


            <div className="step-card">

              <span className="step-number">2</span>

              <h3>Explore Connections</h3>

              <p>
                Actopedia explores their filmographies, collaborators, genres,
                directors, and movie descriptions to discover connected movies.
              </p>

            </div>


            <div className="step-card">

              <span className="step-number">3</span>

              <h3>Discover Movies</h3>

              <p>
                Get a Top 10 ranked by a Match Score based on direct casting
                matches, genres, plot similarity, directors, and collaboration
                networks.
              </p>

            </div>

          </div>

        </section>


        <section>

          <h2>Find Actors/Actresses</h2>

          <div className="search-bar">

            <input
              type="text"
              placeholder="Search for an actor/actress..."
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              onKeyDown={(event) => {

                if (event.key === "Enter") {
                  searchActors();
                }

              }}
            />

            <button onClick={searchActors}>
              {loading ? "Searching..." : "Search"}
            </button>

          </div>


          <div className="search-results">

            {searchResults.map((actor) => (

              <button
                key={actor.id}
                className="search-result"
                onClick={() => selectActor(actor)}
              >

                {actor.profile_path && (

                  <img
                    src={`https://image.tmdb.org/t/p/w185${actor.profile_path}`}
                    alt={actor.name}
                  />

                )}

                <span>{actor.name}</span>

              </button>

            ))}

          </div>

        </section>


        <section>

          <h2>Selected Actors/Actresses ({selectedActors.length}/5)</h2>

          {selectedActors.length === 0 ? (

            <p className="empty-message">
              Search for and select at least two actors/actresses.
            </p>

          ) : (

            <div className="selected-actors">

              {selectedActors.map((actor) => (

                <button
                  key={actor.id}
                  className="actor-card"
                  onClick={() => removeActor(actor.id)}
                >
                  {actor.name} ×
                </button>

              ))}

            </div>

          )}


          <button
            className="recommend-button"
            disabled={selectedActors.length < 2 || recommendationLoading}
            onClick={generateRecommendations}
          >

            {recommendationLoading
              ? "Generating..."
              : "Generate Recommendations"}

          </button>

        </section>


        <section>

          <h2>Recommendations</h2>

          {recommendations.length === 0 ? (

            <p className="empty-message">
              Your Top 10 movie recommendations will appear here.
            </p>

          ) : (

            <div className="recommendation-grid">

              {recommendations.map((movie, index) => (

                <div key={movie.id} className="movie-card">

                  {movie.poster_path && (

                    <img
                      className="movie-poster"
                      src={`https://image.tmdb.org/t/p/w500${movie.poster_path}`}
                      alt={movie.title}
                    />

                  )}

                  <span className="rank">#{index + 1}</span>

                  <h3>{movie.title}</h3>

                  <p>
                    {movie.release_date
                      ? movie.release_date.slice(0, 4)
                      : "Unknown year"}
                  </p>

                  <div className="movie-stats">

                    <span>
                      Rating: {movie.vote_average.toFixed(1)}
                    </span>

                    <span>
                      Match Score: {movie.score.toFixed(1)} / 100
                    </span>

                  </div>

                </div>

              ))}

            </div>

          )}

        </section>


        <section className="faq-section">

          <h2>Frequently Asked Questions</h2>


          <details>

            <summary>How does Actopedia recommend movies?</summary>

            <p>
              Actopedia builds a profile of your selected actors/actresses using
              movies from across their careers. It explores their collaborators
              and connected filmographies, then compares candidate movies using
              direct casting matches, genres, plot descriptions, directors, and
              collaboration networks.
            </p>

          </details>


          <details>

            <summary>What does the Match Score mean?</summary>

            <p>
              The Match Score is Actopedia's recommendation score out of 100.
              A higher score means a movie has a stronger overall connection
              to the actors/actresses you selected and the kinds of movies
              associated with their filmographies.
            </p>

          </details>


          <details>

            <summary>What goes into the Match Score?</summary>

            <div className="score-breakdown">

              <p>
                <strong>Direct Casting Match — 30%</strong>
                <br />
                Rewards movies featuring multiple selected actors/actresses.
                The score increases based on how many of your selected
                actors/actresses appear in the same movie.
              </p>


              <p>
                <strong>Genre Profile — 25%</strong>
                <br />
                Compares the movie's genres with genres that appear frequently
                across the filmographies of your selected actors/actresses.
              </p>


              <p>
                <strong>Plot Description Similarity — 20%</strong>
                <br />
                Compares words in the movie's description with descriptions
                from movies used to build the profiles of your selected
                actors/actresses.
              </p>


              <p>
                <strong>Director Connection — 15%</strong>
                <br />
                Rewards movies directed by filmmakers who also appear across
                the filmographies of your selected actors/actresses.
              </p>


              <p>
                <strong>Collaboration Network — 10%</strong>
                <br />
                Measures connections through collaborators who have worked
                with the selected actors/actresses, with repeated
                collaborations creating stronger connections.
              </p>

            </div>

          </details>


          <details>

            <summary>How many actors/actresses can I select?</summary>

            <p>
              You can select between 2 and 5 actors/actresses. With more
              selections, Actopedia looks for movies and connections that
              overlap with different parts of their combined profiles.
            </p>

          </details>


          <details>

            <summary>
              Why am I seeing movies that don't feature my selected actors/actresses?
            </summary>

            <p>
              Actopedia is designed for discovery rather than simply finding
              movies starring the selected actors/actresses. It explores their
              collaborators and compares connected movies with the genres,
              plot descriptions, directors, and relationships found across
              their filmographies.
            </p>

          </details>


          <details>

            <summary>Where does the movie data come from?</summary>

            <p>
              Actor/actress, movie, cast, genre, director, rating, popularity,
              and image data are provided through The Movie Database (TMDB).
            </p>

          </details>

        </section>

      </main>

    </div>

  );

}

export default App;