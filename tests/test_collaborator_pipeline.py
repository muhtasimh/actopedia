from app.main import accumulate_collaborator_connections


def test_collaborator_counts_preserve_actor_and_movie_order():
    exploration = {10: [100, 101], 20: [101, 102]}
    casts = {
        102: [{"id": 40}, {"id": 30}],
        101: [{"id": 30}, {"id": 40}, {"id": 10}],
        100: [{"id": 30}, {"id": 30}, {"id": 20}],
    }
    result = accumulate_collaborator_connections(exploration, casts, [10, 20])
    assert list(result) == [30, 40]
    assert dict(result[30]) == {10: 3, 20: 1}
    assert dict(result[40]) == {10: 1, 20: 2}


def test_collaborator_counts_exclude_selected_actors():
    result = accumulate_collaborator_connections(
        {10: [100]}, {100: [{"id": 10}, {"id": 20}]}, [10, 20]
    )
    assert not result
