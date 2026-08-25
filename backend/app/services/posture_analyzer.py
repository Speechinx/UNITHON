import math
import statistics


class PostureAnalyzer:
    MIN_VISIBILITY = 0.5
    MIN_VALID_FRAME_RATIO = 0.5

    SHOULDER_TILT_MILD_DEG = 8.0
    SHOULDER_TILT_SEVERE_DEG = 15.0

    HEAD_DOWN_MILD_DEG = 60.0
    HEAD_DOWN_SEVERE_DEG = 75.0

    TORSO_LEAN_MILD_DEG = 10.0
    TORSO_LEAN_SEVERE_DEG = 20.0

    TORSO_LEAN_DIRECTION_Z_THRESHOLD = 0.05

    SWAY_MILD_STD = 0.02
    SWAY_SEVERE_STD = 0.05

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

    ARM_LANDMARKS = [
        "left_elbow",
        "right_elbow",
    ]

    OPEN_POSTURE_CLOSED_MAX = 0.4
    OPEN_POSTURE_OPEN_MIN = 1.0

    GAZE_AWAY_MILD_DEG = 20.0
    GAZE_AWAY_SEVERE_DEG = 35.0

    GAZE_LANDMARKS = [
        "left_ear",
        "right_ear",
    ]

    POWER_ZONE_LOW_MAX = 0.3
    POWER_ZONE_HIGH_MIN = 0.6

    HEAD_ALIGNMENT_MILD_Z = 0.03
    HEAD_ALIGNMENT_SEVERE_Z = 0.07

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

    def _classify(
        self,
        value: float,
        mild: float,
        severe: float,
    ) -> str:

        if value >= severe:
            return "severe"

        if value >= mild:
            return "mild"

        return "stable"

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

    def _shoulder_center_z(
        self,
        frame: dict,
    ) -> float:

        left = frame["left_shoulder"]
        right = frame["right_shoulder"]

        return (left["z"] + right["z"]) / 2

    def _hip_center_z(
        self,
        frame: dict,
    ) -> float:

        left = frame["left_hip"]
        right = frame["right_hip"]

        return (left["z"] + right["z"]) / 2

    def _torso_lean_direction(
        self,
        frame: dict,
    ) -> str:

        dz = (
            self._shoulder_center_z(frame)
            - self._hip_center_z(frame)
        )

        if dz <= -self.TORSO_LEAN_DIRECTION_Z_THRESHOLD:
            return "forward"

        if dz >= self.TORSO_LEAN_DIRECTION_Z_THRESHOLD:
            return "backward"

        return "neutral"

    def _gaze_away_deg(
        self,
        frame: dict,
    ) -> float:

        left_ear = frame["left_ear"]
        right_ear = frame["right_ear"]
        nose = frame["nose"]

        ear_mid_x = (left_ear["x"] + right_ear["x"]) / 2
        ear_half_distance = abs(right_ear["x"] - left_ear["x"]) / 2

        if ear_half_distance == 0:
            return 0.0

        dx = nose["x"] - ear_mid_x

        return abs(
            math.degrees(
                math.atan2(
                    abs(dx),
                    ear_half_distance,
                )
            )
        )

    def _forward_head_z_offset(
        self,
        frame: dict,
    ) -> float:

        ear_center_z = (
            frame["left_ear"]["z"] + frame["right_ear"]["z"]
        ) / 2

        shoulder_center_z = self._shoulder_center_z(frame)

        return shoulder_center_z - ear_center_z

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
                "avatar_state": "unknown",
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

        power_zone_frames = [
            frame
            for frame in valid_frames
            if self._has_signal(frame, self.GESTURE_LANDMARKS)
            and self._has_signal(frame, self.TORSO_LANDMARKS)
        ]

        power_zone_eligible_ratio = (
            len(power_zone_frames) / len(valid_frames)
            if valid_frames
            else 0.0
        )

        if power_zone_eligible_ratio >= self.MIN_VALID_FRAME_RATIO:
            in_zone_count = 0

            for frame in power_zone_frames:
                shoulder_center_y = self._shoulder_center(frame)[1]
                hip_center_y = self._hip_center(frame)[1]

                if (
                    self._in_power_zone(frame["left_wrist"], shoulder_center_y, hip_center_y)
                    or self._in_power_zone(frame["right_wrist"], shoulder_center_y, hip_center_y)
                ):
                    in_zone_count += 1

            power_zone_ratio = in_zone_count / len(power_zone_frames)
            power_zone_level = self._power_zone_level(power_zone_ratio)
        else:
            power_zone_level = "unknown"

        if torso_signal_sufficient:
            torso_leans = [
                self._torso_lean_deg(frame)
                for frame in torso_frames
            ]

            torso_lean_avg = statistics.mean(torso_leans)
            torso_lean_exceed_ratio = self._exceed_ratio(
                torso_leans,
                self.TORSO_LEAN_MILD_DEG,
            )
            torso_lean_level = self._classify(
                torso_lean_avg,
                self.TORSO_LEAN_MILD_DEG,
                self.TORSO_LEAN_SEVERE_DEG,
            )

            torso_directions = [
                self._torso_lean_direction(frame)
                for frame in torso_frames
            ]

            direction_counts = {
                "neutral": torso_directions.count("neutral"),
                "backward": torso_directions.count("backward"),
                "forward": torso_directions.count("forward"),
            }

            torso_lean_direction = max(
                direction_counts,
                key=lambda direction: direction_counts[direction],
            )
        else:
            torso_lean_avg = 0.0
            torso_lean_exceed_ratio = 0.0
            torso_lean_level = "unknown"
            torso_lean_direction = "unknown"

        open_posture_frames = [
            frame
            for frame in valid_frames
            if self._has_signal(frame, self.ARM_LANDMARKS)
            and self._has_signal(frame, self.GESTURE_LANDMARKS)
            and self._has_signal(frame, self.TORSO_LANDMARKS)
        ]

        open_posture_ratio = (
            len(open_posture_frames) / len(valid_frames)
            if valid_frames
            else 0.0
        )

        if open_posture_ratio >= self.MIN_VALID_FRAME_RATIO:
            open_posture_level = self._open_posture_level(
                [
                    self._open_posture_score(frame)
                    for frame in open_posture_frames
                ]
            )
        else:
            open_posture_level = "unknown"

        gaze_frames = [
            frame
            for frame in valid_frames
            if self._has_signal(frame, self.GAZE_LANDMARKS)
        ]

        gaze_ratio = (
            len(gaze_frames) / len(valid_frames)
            if valid_frames
            else 0.0
        )

        gaze_signal_sufficient = (
            gaze_ratio >= self.MIN_VALID_FRAME_RATIO
        )

        if gaze_signal_sufficient:
            gaze_away_degs = [
                self._gaze_away_deg(frame)
                for frame in gaze_frames
            ]

            gaze_away_avg = statistics.mean(gaze_away_degs)
            gaze_away_exceed_ratio = self._exceed_ratio(
                gaze_away_degs,
                self.GAZE_AWAY_MILD_DEG,
            )
            gaze_away_level = self._classify(
                gaze_away_avg,
                self.GAZE_AWAY_MILD_DEG,
                self.GAZE_AWAY_SEVERE_DEG,
            )

            head_alignment_offsets = [
                self._forward_head_z_offset(frame)
                for frame in gaze_frames
            ]

            head_alignment_avg = statistics.mean(head_alignment_offsets)
            head_alignment_exceed_ratio = self._exceed_ratio(
                head_alignment_offsets,
                self.HEAD_ALIGNMENT_MILD_Z,
            )
            head_alignment_level = self._classify(
                head_alignment_avg,
                self.HEAD_ALIGNMENT_MILD_Z,
                self.HEAD_ALIGNMENT_SEVERE_Z,
            )
        else:
            gaze_away_avg = 0.0
            gaze_away_exceed_ratio = 0.0
            gaze_away_level = "unknown"

            head_alignment_avg = 0.0
            head_alignment_exceed_ratio = 0.0
            head_alignment_level = "unknown"

        shoulder_tilt_avg = statistics.mean(shoulder_tilts)
        shoulder_tilt_exceed_ratio = self._exceed_ratio(
            shoulder_tilts,
            self.SHOULDER_TILT_MILD_DEG,
        )

        shoulder_tilt_level = self._classify(
            shoulder_tilt_avg,
            self.SHOULDER_TILT_MILD_DEG,
            self.SHOULDER_TILT_SEVERE_DEG,
        )

        head_down_avg = statistics.mean(head_downs)
        head_down_exceed_ratio = self._exceed_ratio(
            head_downs,
            self.HEAD_DOWN_MILD_DEG,
        )

        head_down_level = self._classify(
            head_down_avg,
            self.HEAD_DOWN_MILD_DEG,
            self.HEAD_DOWN_SEVERE_DEG,
        )

        sway_std = (
            statistics.pstdev(shoulder_centers_x)
            if len(shoulder_centers_x) > 1
            else 0.0
        )

        sway_level = self._classify(
            sway_std,
            self.SWAY_MILD_STD,
            self.SWAY_SEVERE_STD,
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
            if shoulder_tilt_level == "severe":
                reasons.append("어깨가 한쪽으로 많이 기울어져 있었어요")
            elif shoulder_tilt_level == "mild":
                reasons.append("어깨가 약간 기울어진 구간이 있었어요")

        if head_down_exceed_ratio >= self.REASON_EXCEED_RATIO_THRESHOLD:
            if head_down_level == "severe":
                reasons.append("고개를 많이 숙인 채로 발표했어요")
            elif head_down_level == "mild":
                reasons.append("고개를 자주 숙이고 있었어요")

        if (
            torso_signal_sufficient
            and torso_lean_exceed_ratio >= self.REASON_EXCEED_RATIO_THRESHOLD
            and torso_lean_direction != "forward"
        ):
            if torso_lean_level == "severe":
                reasons.append("상체가 많이 기울어져 있었어요")
            elif torso_lean_level == "mild":
                reasons.append("상체가 살짝 기울어져 있었어요")

        if (
            gaze_signal_sufficient
            and gaze_away_exceed_ratio >= self.REASON_EXCEED_RATIO_THRESHOLD
        ):
            if gaze_away_level == "severe":
                reasons.append("시선이 많이 벗어나 있었어요")
            elif gaze_away_level == "mild":
                reasons.append("시선이 자주 옆으로 벗어났어요")

        if (
            gaze_signal_sufficient
            and head_alignment_exceed_ratio >= self.REASON_EXCEED_RATIO_THRESHOLD
        ):
            if head_alignment_level == "severe":
                reasons.append("고개가 어깨보다 많이 앞으로 나와 있었어요")
            elif head_alignment_level == "mild":
                reasons.append("고개가 어깨보다 살짝 앞으로 나와 있었어요")

        if sway_level == "severe":
            reasons.append("몸이 자주 좌우로 흔들렸어요")
        elif sway_level == "mild":
            reasons.append("몸이 조금 흔들렸어요")

        low_engagement = (
            gesture_activity == "low"
            and open_posture_level == "closed"
        )

        if reasons:
            avatar_state = (
                "bored"
                if low_engagement
                else "confused"
            )
        else:
            avatar_state = (
                "focused"
                if low_engagement
                else "engaged"
            )

        return {
            "signal_sufficient": True,
            "valid_frame_ratio": round(valid_ratio, 2),
            "shoulder_tilt_avg_deg": round(shoulder_tilt_avg, 2),
            "shoulder_tilt_exceed_ratio": round(shoulder_tilt_exceed_ratio, 2),
            "shoulder_tilt_level": shoulder_tilt_level,
            "head_down_avg_deg": round(head_down_avg, 2),
            "head_down_exceed_ratio": round(head_down_exceed_ratio, 2),
            "head_down_level": head_down_level,
            "sway_std": round(sway_std, 4),
            "sway_level": sway_level,
            "gesture_activity_level": gesture_activity,
            "torso_signal_sufficient": torso_signal_sufficient,
            "torso_lean_avg_deg": round(torso_lean_avg, 2),
            "torso_lean_exceed_ratio": round(torso_lean_exceed_ratio, 2),
            "torso_lean_level": torso_lean_level,
            "torso_lean_direction": torso_lean_direction,
            "open_posture_level": open_posture_level,
            "gaze_signal_sufficient": gaze_signal_sufficient,
            "gaze_away_avg_deg": round(gaze_away_avg, 2),
            "gaze_away_exceed_ratio": round(gaze_away_exceed_ratio, 2),
            "gaze_away_level": gaze_away_level,
            "head_alignment_level": head_alignment_level,
            "power_zone_level": power_zone_level,
            "reasons": reasons,
            "avatar_state": avatar_state,
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

    def _in_power_zone(
        self,
        wrist: dict,
        shoulder_center_y: float,
        hip_center_y: float,
    ) -> bool:

        return shoulder_center_y <= wrist["y"] <= hip_center_y

    def _power_zone_level(
        self,
        ratio: float,
    ) -> str:

        if ratio < self.POWER_ZONE_LOW_MAX:
            return "low"

        if ratio > self.POWER_ZONE_HIGH_MIN:
            return "high"

        return "normal"

    def _distance(
        self,
        a: dict,
        b: dict,
    ) -> float:

        return math.hypot(
            b["x"] - a["x"],
            b["y"] - a["y"],
        )

    def _open_posture_distance(
        self,
        point: dict,
        shoulder_center: tuple[float, float],
        hip_center: tuple[float, float],
        shoulder_width: float,
    ) -> float:

        ax, ay = hip_center
        bx, by = shoulder_center
        px, py = point["x"], point["y"]

        line_length = math.hypot(bx - ax, by - ay)

        if line_length == 0 or shoulder_width == 0:
            return 0.0

        cross = abs(
            (bx - ax) * (py - ay)
            - (by - ay) * (px - ax)
        )

        return (cross / line_length) / shoulder_width

    def _open_posture_score(
        self,
        frame: dict,
    ) -> float:

        shoulder_center = self._shoulder_center(frame)
        hip_center = self._hip_center(frame)

        shoulder_width = self._distance(
            frame["left_shoulder"],
            frame["right_shoulder"],
        )

        points = [
            frame["left_elbow"],
            frame["right_elbow"],
            frame["left_wrist"],
            frame["right_wrist"],
        ]

        distances = [
            self._open_posture_distance(
                point,
                shoulder_center,
                hip_center,
                shoulder_width,
            )
            for point in points
        ]

        return statistics.mean(distances)

    def _open_posture_level(
        self,
        scores: list[float],
    ) -> str:

        avg_score = statistics.mean(scores)

        if avg_score < self.OPEN_POSTURE_CLOSED_MAX:
            return "closed"

        if avg_score > self.OPEN_POSTURE_OPEN_MIN:
            return "open"

        return "normal"

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
