class PostureWindow {
  const PostureWindow({
    required this.windowIndex,
    required this.signalSufficient,
    required this.shoulderTiltAvgDeg,
    required this.shoulderTiltExceedRatio,
    required this.shoulderTiltLevel,
    required this.headDownAvgDeg,
    required this.headDownExceedRatio,
    required this.headDownLevel,
    required this.swayLevel,
    required this.gestureActivityLevel,
    required this.torsoSignalSufficient,
    required this.torsoLeanAvgDeg,
    required this.torsoLeanExceedRatio,
    required this.torsoLeanLevel,
    required this.torsoLeanDirection,
    required this.openPostureLevel,
    required this.powerZoneLevel,
    required this.gazeAwayLevel,
    required this.headAlignmentLevel,
    required this.reasons,
  });

  final int windowIndex;
  final bool signalSufficient;
  final double shoulderTiltAvgDeg;
  final double shoulderTiltExceedRatio;
  final String shoulderTiltLevel;
  final double headDownAvgDeg;
  final double headDownExceedRatio;
  final String headDownLevel;
  final String swayLevel;
  final String gestureActivityLevel;
  final bool torsoSignalSufficient;
  final double torsoLeanAvgDeg;
  final double torsoLeanExceedRatio;
  final String torsoLeanLevel;
  final String torsoLeanDirection;
  final String openPostureLevel;
  final String powerZoneLevel;
  final String gazeAwayLevel;
  final String headAlignmentLevel;
  final List<String> reasons;

  factory PostureWindow.fromJson(Map<String, dynamic> json) {
    return PostureWindow(
      windowIndex: json['window_index'] as int? ?? 0,
      signalSufficient: json['signal_sufficient'] as bool? ?? false,
      shoulderTiltAvgDeg:
          (json['shoulder_tilt_avg_deg'] as num?)?.toDouble() ?? 0.0,
      shoulderTiltExceedRatio:
          (json['shoulder_tilt_exceed_ratio'] as num?)?.toDouble() ?? 0.0,
      shoulderTiltLevel: json['shoulder_tilt_level'] as String? ?? 'unknown',
      headDownAvgDeg:
          (json['head_down_avg_deg'] as num?)?.toDouble() ?? 0.0,
      headDownExceedRatio:
          (json['head_down_exceed_ratio'] as num?)?.toDouble() ?? 0.0,
      headDownLevel: json['head_down_level'] as String? ?? 'unknown',
      swayLevel: json['sway_level'] as String? ?? 'unknown',
      gestureActivityLevel:
          json['gesture_activity_level'] as String? ?? 'unknown',
      torsoSignalSufficient:
          json['torso_signal_sufficient'] as bool? ?? false,
      torsoLeanAvgDeg:
          (json['torso_lean_avg_deg'] as num?)?.toDouble() ?? 0.0,
      torsoLeanExceedRatio:
          (json['torso_lean_exceed_ratio'] as num?)?.toDouble() ?? 0.0,
      torsoLeanLevel: json['torso_lean_level'] as String? ?? 'unknown',
      torsoLeanDirection:
          json['torso_lean_direction'] as String? ?? 'unknown',
      openPostureLevel: json['open_posture_level'] as String? ?? 'unknown',
      powerZoneLevel: json['power_zone_level'] as String? ?? 'unknown',
      gazeAwayLevel: json['gaze_away_level'] as String? ?? 'unknown',
      headAlignmentLevel:
          json['head_alignment_level'] as String? ?? 'unknown',
      reasons:
          (json['reasons'] as List?)?.whereType<String>().toList() ?? [],
    );
  }
}
