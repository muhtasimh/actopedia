"""Equivalence checks for sparse description preselection."""
import random

from app.main import (
    build_profile_word_index,
    jaccard_similarity,
    strongest_description_similarity,
)


def original_score(candidate, profiles):
    similarities = sorted(
        (jaccard_similarity(candidate, profile) for profile in profiles),
        reverse=True,
    )
    strongest = similarities[:3]
    return sum(strongest) / len(strongest) if strongest else 0


def test_sparse_similarity_matches_original_randomized():
    rng = random.Random(1234)
    vocabulary = [f"word{i}" for i in range(100)]
    for profile_count in (0, 1, 2, 3, 15, 30):
        for _ in range(100):
            profiles = [
                set(rng.sample(vocabulary, rng.randrange(1, 12)))
                for _ in range(profile_count)
            ]
            candidate = set(rng.sample(vocabulary, rng.randrange(0, 12)))
            index = build_profile_word_index(profiles)
            assert strongest_description_similarity(
                candidate, profiles, index
            ) == original_score(candidate, profiles)


def test_sparse_similarity_preserves_nonmatching_zero_scores():
    profiles = [{"space", "travel"}, {"drama"}, {"comedy"}, {"romance"}]
    index = build_profile_word_index(profiles)
    assert strongest_description_similarity(
        {"space"}, profiles, index
    ) == original_score({"space"}, profiles)
