class PostureWindow {
  const PostureWindow({
    required this.windowIndex,
    required this.signalSufficient,
    required this.shoulderTiltAvgDeg,
    required this.shoulderTiltExceedRatio,
    required this.headDownAvgDeg,
    required this.headDownExceedRatio,
    required this.gestureActivityLevel,
    required this.torsoSignalSufficient,
    required this.torsoLeanAvgDeg,
    required this.torsoLeanExceedRatio,
    required this.armOpennessLevel,
    required this.reasons,
  });

  final int windowIndex;
  final bool signalSufficient;
  final double shoulderTiltAvgDeg;
  final double shoulderTiltExceedRatio;
  final double headDownAvgDeg;
  final double headDownExceedRatio;
  final String gestureActivityLevel;
  final bool torsoSignalSufficient;
  final double torsoLeanAvgDeg;
  final double torsoLeanExceedRatio;
  final String armOpennessLevel;
  final List<String> reasons;

  factory PostureWindow.fromJson(Map<String, dynamic> json) {
    return PostureWindow(
      windowIndex: json['window_index'] as int? ?? 0,
      signalSufficient: json['signal_sufficient'] as bool? ?? false,
      shoulderTiltAvgDeg:
          (json['shoulder_tilt_avg_deg'] as num?)?.toDouble() ?? 0.0,
      shoulderTiltExceedRatio:
          (json['shoulder_tilt_exceed_ratio'] as num?)?.toDouble() ?? 0.0,
      headDownAvgDeg:
          (json['head_down_avg_deg'] as num?)?.toDouble() ?? 0.0,
      headDownExceedRatio:
          (json['head_down_exceed_ratio'] as num?)?.toDouble() ?? 0.0,
      gestureActivityLevel:
          json['gesture_activity_level'] as String? ?? 'unknown',
      torsoSignalSufficient:
          json['torso_signal_sufficient'] as bool? ?? false,
      torsoLeanAvgDeg:
          (json['torso_lean_avg_deg'] as num?)?.toDouble() ?? 0.0,
      torsoLeanExceedRatio:
          (json['torso_lean_exceed_ratio'] as num?)?.toDouble() ?? 0.0,
      armOpennessLevel:
          json['arm_openness_level'] as String? ?? 'unknown',
      reasons:
          (json['reasons'] as List?)?.whereType<String>().toList() ?? [],
    );
  }
}
