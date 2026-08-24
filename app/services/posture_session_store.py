class PostureSessionStore:
    def __init__(self):
        self._sessions: dict[str, dict[int, dict]] = {}

    def add_window(
        self,
        session_id: str,
        window_index: int,
        result: dict,
    ) -> None:

        self._sessions.setdefault(
            session_id,
            {},
        )[window_index] = result

    def get_windows(
        self,
        session_id: str,
    ) -> list[dict]:

        windows = self._sessions.get(
            session_id,
            {},
        )

        return [
            windows[index]
            for index in sorted(windows.keys())
        ]

    def clear(
        self,
        session_id: str,
    ) -> None:

        self._sessions.pop(session_id, None)
