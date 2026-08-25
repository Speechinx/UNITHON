import 'package:flutter/material.dart';

import '../theme/app_colors.dart';

enum AppTab { home, history, mypage }

enum HomeScreen { start, recording, loading, summary, detail }

enum RecordMode { voice, voiceMotion }

enum DetailTab { flow, improve, script }

enum SegmentLevel { stable, caution, danger }

extension SegmentLevelX on SegmentLevel {
  String get label => switch (this) {
        SegmentLevel.stable => '안정',
        SegmentLevel.caution => '주의',
        SegmentLevel.danger => '위험',
      };

  Color get color => switch (this) {
        SegmentLevel.stable => AppColors.green500,
        SegmentLevel.caution => AppColors.amber500,
        SegmentLevel.danger => AppColors.red500,
      };

  Color get badgeBg => switch (this) {
        SegmentLevel.stable => AppColors.green100,
        SegmentLevel.caution => AppColors.amber100,
        SegmentLevel.danger => AppColors.red100,
      };

  Color get badgeFg => switch (this) {
        SegmentLevel.stable => AppColors.green700,
        SegmentLevel.caution => AppColors.amber700,
        SegmentLevel.danger => AppColors.red600,
      };
}

class Segment {
  const Segment({
    required this.level,
    required this.time,
    required this.flex,
    required this.scoreLabel,
    required this.score,
    required this.scoreColor,
    required this.speed,
    required this.tone,
    required this.pause,
    required this.filler,
    required this.repeat,
    required this.signals,
    required this.script,
    required this.postureAvailable,
    required this.postureSignalSufficient,
    required this.shoulderTilt,
    required this.headDown,
    required this.torsoLean,
    required this.armOpenness,
    required this.gestureActivity,
    required this.postureReasons,
  });

  final SegmentLevel level;
  final String time;

  /// 타임라인에서 차지하는 비율 (원본의 width % 값).
  final int flex;
  final String scoreLabel;
  final String score;
  final Color scoreColor;
  final String speed;
  final String tone;
  final String pause;
  final String filler;
  final String repeat;
  final List<String> signals;
  final String script;

  /// 이 구간에 자세(카메라) 데이터가 있는지 여부.
  final bool postureAvailable;
  final bool postureSignalSufficient;
  final String shoulderTilt;
  final String headDown;
  final String torsoLean;
  final String armOpenness;
  final String gestureActivity;
  final List<String> postureReasons;
}

class HistoryItem {
  const HistoryItem({
    required this.date,
    required this.badge,
    required this.title,
    required this.detail,
  });

  final String date;
  final String badge;
  final String title;
  final String detail;
}

class MetricData {
  const MetricData({
    required this.label,
    required this.value,
    required this.sub,
    required this.icon,
    required this.iconColor,
  });

  final String label;
  final String value;
  final String sub;
  final IconData icon;
  final Color iconColor;
}
