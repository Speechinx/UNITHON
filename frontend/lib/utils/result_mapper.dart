import 'package:flutter/material.dart';

import '../models/app_models.dart';
import '../posture/posture_timeline.dart';
import '../theme/app_colors.dart';

/// 백엔드 `/analyze` 응답(Map)을 화면 위젯이 바로 쓸 수 있는 모델로 변환하는
/// 순수 함수 모음.

/// 백엔드가 내려주는 `score`는 감점이 누적되는 "위험 점수"(0=완벽, 100=최악)다.
/// 화면에는 "발표 점수"(높을수록 좋음)로 뒤집어 보여준다.
int presentationScoreFromRisk(num riskScore) {
  return (100 - riskScore).clamp(0, 100).round();
}

/// 발표 점수(0~100, 높을수록 좋음) 기준: 70점 이상 안정, 50~69점 주의, 그 미만 위험.
SegmentLevel levelFromScore(int presentationScore) {
  if (presentationScore >= 70) {
    return SegmentLevel.stable;
  }
  if (presentationScore >= 50) {
    return SegmentLevel.caution;
  }
  return SegmentLevel.danger;
}

String paceText(String? level) {
  switch (level) {
    case 'slow':
      return '느림';
    case 'slightly_slow':
      return '약간 느림';
    case 'normal':
      return '적절';
    case 'slightly_fast':
      return '약간 빠름';
    case 'fast':
      return '빠름';
    default:
      return '판정 없음';
  }
}

String emotionText(String? emotion) {
  switch (emotion?.toLowerCase()) {
    case 'neutral':
      return '차분한 톤';
    case 'happy':
      return '밝은 톤';
    case 'sad':
      return '가라앉은 톤';
    case 'angry':
      return '강한 톤';
    case 'fearful':
      return '불안정한 톤';
    case 'surprised':
      return '변화가 큰 톤';
    case 'disgusted':
      return '거친 톤';
    case 'emo_unknown':
    case 'unknown':
      return '톤 신호 부족';
    default:
      return '분석 불가';
  }
}

String gestureActivityText(String level) {
  switch (level) {
    case 'low':
      return '낮음';
    case 'normal':
      return '보통';
    case 'high':
      return '높음';
    default:
      return '분석 없음';
  }
}

String armOpennessText(String level) {
  switch (level) {
    case 'closed':
      return '닫힘';
    case 'normal':
      return '보통';
    case 'open':
      return '열림';
    default:
      return '분석 없음';
  }
}

String _replaceBackendTerms(String text) {
  return text.replaceAll('pause', '멈춤').replaceAll('Pause', '멈춤');
}

double asDouble(dynamic value) {
  if (value is num) {
    return value.toDouble();
  }
  return 0.0;
}

String formatTime(double seconds) {
  final totalSeconds = seconds.round();
  final minutes = totalSeconds ~/ 60;
  final remainingSeconds = totalSeconds % 60;

  if (minutes > 0) {
    return '$minutes:${remainingSeconds.toString().padLeft(2, '0')}';
  }
  return '$totalSeconds초';
}

String formatHistoryDuration(double seconds) {
  final totalSeconds = seconds.round();
  final minutes = totalSeconds ~/ 60;
  final remaining = totalSeconds % 60;

  if (minutes == 0) {
    return '$remaining초';
  }
  return '$minutes분 $remaining초';
}

String formatHistoryDate(DateTime? date) {
  if (date == null) {
    return '날짜 정보 없음';
  }

  final local = date.toLocal();
  final month = local.month.toString().padLeft(2, '0');
  final day = local.day.toString().padLeft(2, '0');
  final hour = local.hour.toString().padLeft(2, '0');
  final minute = local.minute.toString().padLeft(2, '0');

  return '${local.year}.$month.$day  $hour:$minute';
}

Map<String, dynamic> _asMap(dynamic value) {
  if (value is Map) {
    return Map<String, dynamic>.from(value);
  }
  return <String, dynamic>{};
}

List<Map<String, dynamic>> _asMapList(dynamic value) {
  if (value is List) {
    return value
        .whereType<Map>()
        .map((item) => Map<String, dynamic>.from(item))
        .toList();
  }
  return <Map<String, dynamic>>[];
}

({String summary, SegmentLevel level}) buildOverall(
  Map<String, dynamic> result,
) {
  final coaching = _asMap(result['coaching']);
  final risk = _asMap(result['risk']);
  final presentationScore = presentationScoreFromRisk(
    asDouble(risk['overall_score']),
  );

  return (
    summary: coaching['summary']?.toString() ?? '',
    level: levelFromScore(presentationScore),
  );
}

({int fillerCount, int repetitionCount}) _fillerCounts(
  Map<String, dynamic> result,
) {
  final fillers = _asMapList(result['fillers']);

  var fillerCount = 0;
  var repetitionCount = 0;

  for (final event in fillers) {
    if (event['type'] == 'filler') fillerCount++;
    if (event['type'] == 'repetition') repetitionCount++;
  }

  return (fillerCount: fillerCount, repetitionCount: repetitionCount);
}

List<MetricData> buildMetrics(Map<String, dynamic> result) {
  final speech = _asMap(result['speech']);
  final counts = _fillerCounts(result);

  final rate = asDouble(speech['presentation_rate']);
  final pauseRatio = asDouble(speech['internal_pause_ratio']) * 100;

  return [
    MetricData(
      label: '발표 속도',
      value: paceText(speech['pace_level']?.toString()),
      sub: '${rate.toStringAsFixed(0)}어/분',
      icon: Icons.access_time,
      iconColor: AppColors.violet600,
    ),
    MetricData(
      label: '멈춤 비율',
      value: '${pauseRatio.toStringAsFixed(1)}%',
      sub: '전체 대비',
      icon: Icons.error_outline,
      iconColor: AppColors.amber500,
    ),
    MetricData(
      label: '추임새 횟수',
      value: '${counts.fillerCount}회',
      sub: '총 횟수',
      icon: Icons.warning_amber_rounded,
      iconColor: AppColors.amber500,
    ),
    MetricData(
      label: '반복 횟수',
      value: '${counts.repetitionCount}회',
      sub: '총 횟수',
      icon: Icons.repeat,
      iconColor: AppColors.emerald500,
    ),
  ];
}

Color _scoreColor(SegmentLevel level) {
  switch (level) {
    case SegmentLevel.stable:
      return AppColors.green600;
    case SegmentLevel.caution:
      return AppColors.amber600;
    case SegmentLevel.danger:
      return AppColors.red500;
  }
}

/// `posture.windows`를 `window_index` 기준으로 인덱싱한다. 자세 캡처가
/// 없었던 세션(voice 전용 모드)은 빈 맵을 반환한다.
Map<int, PostureWindow> _postureWindowsByIndex(Map<String, dynamic> result) {
  final posture = _asMap(result['posture']);
  final windows = _asMapList(posture['windows']);
  final byIndex = <int, PostureWindow>{};

  for (final windowJson in windows) {
    final window = PostureWindow.fromJson(windowJson);
    byIndex[window.windowIndex] = window;
  }

  return byIndex;
}

List<Segment> buildSegments(Map<String, dynamic> result) {
  final risk = _asMap(result['risk']);
  final heatmap = _asMapList(risk['heatmap']);
  final postureWindows = _postureWindowsByIndex(result);

  return heatmap.asMap().entries.map((entry) {
    final index = entry.key;
    final window = entry.value;

    final start = asDouble(window['start']);
    final end = asDouble(window['end']);
    final presentationScore = presentationScoreFromRisk(
      asDouble(window['score']),
    );
    final level = levelFromScore(presentationScore);
    final duration = (end - start).clamp(0.1, double.infinity);

    final reasons = List<String>.from(window['reasons'] ?? []);
    final postureWindow = postureWindows[index];

    return Segment(
      level: level,
      time: '${formatTime(start)} ~ ${formatTime(end)}',
      flex: (duration * 10).round().clamp(1, 999),
      scoreLabel: '발표 점수',
      score: '$presentationScore점',
      scoreColor: _scoreColor(level),
      speed: paceText(window['pace_level']?.toString()),
      tone: emotionText(window['emotion_signal']?.toString()),
      pause: '${window['pause_count'] ?? 0}회',
      filler: '${window['filler_count'] ?? 0}회',
      repeat: '${window['repetition_count'] ?? 0}회',
      signals: reasons.map(_replaceBackendTerms).toList(),
      script: window['transcript']?.toString().trim() ?? '',
      postureAvailable: postureWindow != null,
      postureSignalSufficient: postureWindow?.signalSufficient ?? false,
      shoulderTilt: postureWindow == null
          ? ''
          : '평균 ${postureWindow.shoulderTiltAvgDeg.toStringAsFixed(1)}도 '
              '· 초과 ${(postureWindow.shoulderTiltExceedRatio * 100).toStringAsFixed(0)}%',
      headDown: postureWindow == null
          ? ''
          : '평균 ${postureWindow.headDownAvgDeg.toStringAsFixed(1)}도 '
              '· 초과 ${(postureWindow.headDownExceedRatio * 100).toStringAsFixed(0)}%',
      torsoLean: postureWindow == null
          ? ''
          : (postureWindow.torsoSignalSufficient
              ? '평균 ${postureWindow.torsoLeanAvgDeg.toStringAsFixed(1)}도 '
                  '· 초과 ${(postureWindow.torsoLeanExceedRatio * 100).toStringAsFixed(0)}%'
              : '상체 기울기 신호 부족'),
      armOpenness:
          postureWindow == null ? '' : armOpennessText(postureWindow.armOpennessLevel),
      gestureActivity: postureWindow == null
          ? ''
          : gestureActivityText(postureWindow.gestureActivityLevel),
      postureReasons: postureWindow?.reasons ?? const [],
    );
  }).toList();
}

List<String> buildStrengths(Map<String, dynamic> result) {
  final coaching = _asMap(result['coaching']);
  return List<String>.from(coaching['strengths'] ?? []);
}

String buildOneLineCoaching(Map<String, dynamic> result) {
  final coaching = _asMap(result['coaching']);
  return coaching['one_line_coaching']?.toString() ?? '';
}

List<Map<String, dynamic>> buildImprovements(Map<String, dynamic> result) {
  final coaching = _asMap(result['coaching']);
  return _asMapList(coaching['improvements']);
}

List<String> buildPracticeGoals(Map<String, dynamic> result) {
  final coaching = _asMap(result['coaching']);
  return List<String>.from(coaching['practice_goals'] ?? []);
}

String buildFullScript(Map<String, dynamic> result) {
  return result['transcript']?.toString() ?? '';
}

HistoryItem buildHistoryItem(Map<String, dynamic> result, DateTime? savedAt) {
  final speech = _asMap(result['speech']);
  final risk = _asMap(result['risk']);
  final counts = _fillerCounts(result);

  final duration = asDouble(result['duration']);
  final rate = asDouble(speech['presentation_rate']);
  final pace = paceText(speech['pace_level']?.toString());
  final presentationScore = presentationScoreFromRisk(
    asDouble(risk['overall_score']),
  );
  final level = levelFromScore(presentationScore);

  return HistoryItem(
    date: formatHistoryDate(savedAt),
    level: level,
    badge: level.label,
    title: '${formatHistoryDuration(duration)} · $pace',
    detail:
        '${rate.toStringAsFixed(0)} 어절/분 · 추임새 ${counts.fillerCount}회 · 반복 ${counts.repetitionCount}회',
  );
}
