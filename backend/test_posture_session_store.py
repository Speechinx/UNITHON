from app.services.posture_session_store import (
    PostureSessionStore,
)


def test_get_windows_returns_sorted_by_index():
    store = PostureSessionStore()

    store.add_window("abc", 1, {"score": 10})
    store.add_window("abc", 0, {"score": 5})

    assert store.get_windows("abc") == [
        {"score": 5},
        {"score": 10},
    ]


def test_get_windows_unknown_session_returns_empty_list():
    store = PostureSessionStore()

    assert store.get_windows("nope") == []


def test_clear_removes_session():
    store = PostureSessionStore()

    store.add_window("abc", 0, {"score": 5})
    store.clear("abc")

    assert store.get_windows("abc") == []


def test_sessions_are_isolated():
    store = PostureSessionStore()

    store.add_window("abc", 0, {"score": 1})
    store.add_window("xyz", 0, {"score": 2})

    assert store.get_windows("abc") == [{"score": 1}]
    assert store.get_windows("xyz") == [{"score": 2}]
