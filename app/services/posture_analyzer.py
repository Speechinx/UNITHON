import math


class PostureAnalyzer:
    MIN_VISIBILITY = 0.5

    REQUIRED_LANDMARKS = [
        "nose",
        "left_shoulder",
        "right_shoulder",
        "left_wrist",
        "right_wrist",
    ]

    def _is_valid(
        self,
        frame: dict | None,
    ) -> bool:

        if frame is None:
            return False

        return all(
            key in frame
            and frame[key]["visibility"] >= self.MIN_VISIBILITY
            for key in self.REQUIRED_LANDMARKS
        )

    def _shoulder_tilt_deg(
        self,
        frame: dict,
    ) -> float:

        left = frame["left_shoulder"]
        right = frame["right_shoulder"]

        dx = right["x"] - left["x"]
        dy = right["y"] - left["y"]

        return abs(
            math.degrees(
                math.atan2(dy, dx)
            )
        )

    def _head_down_deg(
        self,
        frame: dict,
    ) -> float:

        left = frame["left_shoulder"]
        right = frame["right_shoulder"]
        nose = frame["nose"]

        mid_x = (left["x"] + right["x"]) / 2
        mid_y = (left["y"] + right["y"]) / 2

        dx = nose["x"] - mid_x
        dy = nose["y"] - mid_y

        magnitude = math.hypot(dx, dy)

        if magnitude == 0:
            return 0.0

        cos_angle = -dy / magnitude
        cos_angle = max(-1.0, min(1.0, cos_angle))

        return math.degrees(
            math.acos(cos_angle)
        )
