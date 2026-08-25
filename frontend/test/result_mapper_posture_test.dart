import 'package:flutter_test/flutter_test.dart';
import 'package:pr_front/utils/result_mapper.dart' as mapper;

void main() {
  test('buildSegments fills posture fields when posture windows are present', () {
    final result = {
      'risk': {
        'heatmap': [
          {
            'start': 0.0,
            'end': 15.0,
            'level': 'low',
            'score': 90,
            'pace_level': 'normal',
            'emotion_signal': 'neutral',
            'pause_count': 1,
            'filler_count': 0,
            'repetition_count': 0,
            'reasons': <String>[],
            'transcript': '안녕하세요',
          },
        ],
      },
      'posture': {
        'windows': [
          {
            'window_index': 0,
            'signal_sufficient': true,
            'shoulder_tilt_level': 'mild',
            'head_down_level': 'stable',
            'gesture_activity_level': 'normal',
            'torso_signal_sufficient': true,
            'torso_lean_level': 'stable',
            'torso_lean_direction': 'forward',
            'open_posture_level': 'open',
            'power_zone_level': 'high',
            'head_alignment_level': 'mild',
            'reasons': ['어깨가 약간 기울어진 구간이 있었어요'],
          },
        ],
      },
    };

    final segments = mapper.buildSegments(result);

    expect(segments.length, 1);
    expect(segments.first.postureAvailable, true);
    expect(segments.first.postureSignalSufficient, true);
    expect(segments.first.shoulderTilt, '약간 기울어짐');
    expect(segments.first.headDown, '안정');
    expect(segments.first.torsoLean, '안정');
    expect(segments.first.openPosture, '열림');
    expect(segments.first.powerZone, '높음');
    expect(segments.first.headAlignment, '약간 기울어짐');
    expect(segments.first.torsoLeanDirection, '앞으로');
    expect(segments.first.gestureActivity, '보통');
    expect(segments.first.postureReasons, ['어깨가 약간 기울어진 구간이 있었어요']);
  });

  test(
    'buildSegments leaves posture fields empty when posture data is absent',
    () {
      final result = {
        'risk': {
          'heatmap': [
            {
              'start': 0.0,
              'end': 15.0,
              'level': 'low',
              'score': 90,
              'reasons': <String>[],
            },
          ],
        },
      };

      final segments = mapper.buildSegments(result);

      expect(segments.first.postureAvailable, false);
      expect(segments.first.postureSignalSufficient, false);
      expect(segments.first.shoulderTilt, '');
      expect(segments.first.postureReasons, <String>[]);
    },
  );

  test('buildSegments reports insufficient torso signal separately', () {
    final result = {
      'risk': {
        'heatmap': [
          {'start': 0.0, 'end': 15.0, 'level': 'low', 'score': 90, 'reasons': <String>[]},
        ],
      },
      'posture': {
        'windows': [
          {
            'window_index': 0,
            'signal_sufficient': true,
            'torso_signal_sufficient': false,
          },
        ],
      },
    };

    final segments = mapper.buildSegments(result);

    expect(segments.first.torsoLean, '상체 기울기 신호 부족');
  });

  test('gestureActivityText maps known levels', () {
    expect(mapper.gestureActivityText('low'), '낮음');
    expect(mapper.gestureActivityText('normal'), '보통');
    expect(mapper.gestureActivityText('high'), '높음');
    expect(mapper.gestureActivityText('unknown'), '분석 없음');
  });

  test('levelText maps stable/mild/severe/unknown', () {
    expect(mapper.levelText('stable'), '안정');
    expect(mapper.levelText('mild'), '약간 기울어짐');
    expect(mapper.levelText('severe'), '많이 기울어짐');
    expect(mapper.levelText('unknown'), '분석 없음');
  });

  test('openPostureText maps closed/normal/open/unknown', () {
    expect(mapper.openPostureText('closed'), '닫힘');
    expect(mapper.openPostureText('normal'), '보통');
    expect(mapper.openPostureText('open'), '열림');
    expect(mapper.openPostureText('unknown'), '분석 없음');
  });

  test('powerZoneText maps low/normal/high/unknown', () {
    expect(mapper.powerZoneText('low'), '낮음');
    expect(mapper.powerZoneText('normal'), '보통');
    expect(mapper.powerZoneText('high'), '높음');
    expect(mapper.powerZoneText('unknown'), '분석 없음');
  });

  test('torsoLeanDirectionText maps forward/backward/neutral/unknown', () {
    expect(mapper.torsoLeanDirectionText('forward'), '앞으로');
    expect(mapper.torsoLeanDirectionText('backward'), '뒤로');
    expect(mapper.torsoLeanDirectionText('neutral'), '중립');
    expect(mapper.torsoLeanDirectionText('unknown'), '분석 없음');
  });
}
