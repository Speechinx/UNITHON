import math
import statistics


class PostureAnalyzer:
    MIN_VISIBILITY = 0.5
    MIN_VALID_FRAME_RATIO = 0.5

    SHOULDER_TILT_THRESHOLD_DEG = 8.0
    HEAD_DOWN_THRESHOLD_DEG = 60.0
    TORSO_LEAN_THRESHOLD_DEG = 10.0

    REASON_EXCEED_RATIO_THRESHOLD = 0.3

    GESTURE_LOW_THRESHOLD = 0.01
    GESTURE_HIGH_THRESHOLD = 0.05

    REQUIRED_LANDMARKS = [
        "nose",
        "left_shoulder",
        "right_shoulder",
    ]

    GESTURE_LANDMARKS = [
        "left_wrist",
        "right_wrist",
    ]

    TORSO_LANDMARKS = [
        "left_hip",
        "right_hip",
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

    def _has_signal(
        self,
        frame: dict,
        landmark_names: list[str],
    ) -> bool:

        return all(
            key in frame
            and frame[key]["visibility"] >= self.MIN_VISIBILITY
            for key in landmark_names
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
                math.atan2(
                    abs(dy),
                    abs(dx),
                )
            )
        )

    def _head_down_deg(
        self,
        frame: dict,
    ) -> float:

        left = frame["left_shoulder"]
        right = frame["right_shoulder"]
        nose = frame["nose"]

        mid_y = (left["y"] + right["y"]) / 2

        shoulder_width = math.hypot(
            right["x"] - left["x"],
            right["y"] - left["y"],
        )

        if shoulder_width == 0:
            return 0.0

        dy = nose["y"] - mid_y

        return abs(
            math.degrees(
                math.atan2(
                    shoulder_width,
                    -dy,
                )
            )
        )

    def _shoulder_center(
        self,
        frame: dict,
    ) -> tuple[float, float]:

        left = frame["left_shoulder"]
        right = frame["right_shoulder"]

        return (
            (left["x"] + right["x"]) / 2,
            (left["y"] + right["y"]) / 2,
        )

    def _hip_center(
        self,
        frame: dict,
    ) -> tuple[float, float]:

        left = frame["left_hip"]
        right = frame["right_hip"]

        return (
            (left["x"] + right["x"]) / 2,
            (left["y"] + right["y"]) / 2,
        )

    def _torso_lean_deg(
        self,
        frame: dict,
    ) -> float:

        shoulder_x, shoulder_y = self._shoulder_center(frame)
        hip_x, hip_y = self._hip_center(frame)

        dx = shoulder_x - hip_x
        dy = shoulder_y - hip_y

        return abs(
            math.degrees(
                math.atan2(
                    abs(dx),
                    abs(dy),
                )
            )
        )

    def analyze_window(
        self,
        frames: list[dict | None],
    ) -> dict:

        valid_frames = [
            frame
            for frame in frames
            if self._is_valid(frame)
        ]

        valid_ratio = (
            len(valid_frames) / len(frames)
            if frames
            else 0.0
        )

        if valid_ratio < self.MIN_VALID_FRAME_RATIO:
            return {
                "signal_sufficient": False,
                "valid_frame_ratio": round(valid_ratio, 2),
            }

        shoulder_tilts = [
            self._shoulder_tilt_deg(frame)
            for frame in valid_frames
        ]

        head_downs = [
            self._head_down_deg(frame)
            for frame in valid_frames
        ]

        shoulder_centers_x = [
            self._shoulder_center_x(frame)
            for frame in valid_frames
        ]

        gesture_frames = [
            frame
            for frame in valid_frames
            if self._has_signal(frame, self.GESTURE_LANDMARKS)
        ]

        gesture_ratio = (
            len(gesture_frames) / len(valid_frames)
            if valid_frames
            else 0.0
        )

        torso_frames = [
            frame
            for frame in valid_frames
            if self._has_signal(frame, self.TORSO_LANDMARKS)
        ]

        torso_ratio = (
            len(torso_frames) / len(valid_frames)
            if valid_frames
            else 0.0
        )

        torso_signal_sufficient = (
            torso_ratio >= self.MIN_VALID_FRAME_RATIO
        )

        if torso_signal_sufficient:
            torso_leans = [
                self._torso_lean_deg(frame)
                for frame in torso_frames
            ]

            torso_lean_avg = statistics.mean(torso_leans)
            torso_lean_exceed_ratio = self._exceed_ratio(
                torso_leans,
                self.TORSO_LEAN_THRESHOLD_DEG,
            )
        else:
            torso_lean_avg = 0.0
            torso_lean_exceed_ratio = 0.0

        shoulder_tilt_avg = statistics.mean(shoulder_tilts)
        shoulder_tilt_exceed_ratio = self._exceed_ratio(
            shoulder_tilts,
            self.SHOULDER_TILT_THRESHOLD_DEG,
        )

        head_down_avg = statistics.mean(head_downs)
        head_down_exceed_ratio = self._exceed_ratio(
            head_downs,
            self.HEAD_DOWN_THRESHOLD_DEG,
        )

        sway_std = (
            statistics.pstdev(shoulder_centers_x)
            if len(shoulder_centers_x) > 1
            else 0.0
        )

        if gesture_ratio >= self.MIN_VALID_FRAME_RATIO:
            wrist_series = [
                self._wrist_positions(frame)
                for frame in gesture_frames
            ]

            gesture_activity = self._gesture_activity_level(
                wrist_series
            )
        else:
            gesture_activity = "unknown"

        reasons = []

        if shoulder_tilt_exceed_ratio >= self.REASON_EXCEED_RATIO_THRESHOLD:
            reasons.append(
                f"어깨 기울어짐 {shoulder_tilt_exceed_ratio * 100:.0f}% 구간"
            )

        if head_down_exceed_ratio >= self.REASON_EXCEED_RATIO_THRESHOLD:
            reasons.append(
                f"고개 숙임 {head_down_exceed_ratio * 100:.0f}% 구간"
            )

        if (
            torso_signal_sufficient
            and torso_lean_exceed_ratio >= self.REASON_EXCEED_RATIO_THRESHOLD
        ):
            reasons.append(
                f"상체 기울어짐 {torso_lean_exceed_ratio * 100:.0f}% 구간"
            )

        return {
            "signal_sufficient": True,
            "valid_frame_ratio": round(valid_ratio, 2),
            "shoulder_tilt_avg_deg": round(shoulder_tilt_avg, 2),
            "shoulder_tilt_exceed_ratio": round(shoulder_tilt_exceed_ratio, 2),
            "head_down_avg_deg": round(head_down_avg, 2),
            "head_down_exceed_ratio": round(head_down_exceed_ratio, 2),
            "sway_std": round(sway_std, 4),
            "gesture_activity_level": gesture_activity,
            "torso_signal_sufficient": torso_signal_sufficient,
            "torso_lean_avg_deg": round(torso_lean_avg, 2),
            "torso_lean_exceed_ratio": round(torso_lean_exceed_ratio, 2),
            "reasons": reasons,
        }

    def _shoulder_center_x(
        self,
        frame: dict,
    ) -> float:

        left = frame["left_shoulder"]
        right = frame["right_shoulder"]

        return (left["x"] + right["x"]) / 2

    def _wrist_positions(
        self,
        frame: dict,
    ) -> tuple[float, float, float, float]:

        left = frame["left_wrist"]
        right = frame["right_wrist"]

        return (
            left["x"],
            left["y"],
            right["x"],
            right["y"],
        )

    def _gesture_activity_level(
        self,
        wrist_series: list[tuple[float, float, float, float]],
    ) -> str:

        if len(wrist_series) < 2:
            return "low"

        total_movement = 0.0

        for previous, current in zip(
            wrist_series,
            wrist_series[1:],
        ):
            lx0, ly0, rx0, ry0 = previous
            lx1, ly1, rx1, ry1 = current

            total_movement += math.hypot(
                lx1 - lx0,
                ly1 - ly0,
            )

            total_movement += math.hypot(
                rx1 - rx0,
                ry1 - ry0,
            )

        avg_movement = total_movement / (len(wrist_series) - 1)

        if avg_movement < self.GESTURE_LOW_THRESHOLD:
            return "low"

        if avg_movement > self.GESTURE_HIGH_THRESHOLD:
            return "high"

        return "normal"

    def _exceed_ratio(
        self,
        values: list[float],
        threshold: float,
    ) -> float:

        if not values:
            return 0.0

        exceeding = sum(
            1
            for value in values
            if value >= threshold
        )

        return exceeding / len(values)
