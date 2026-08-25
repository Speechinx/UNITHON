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
            'shoulder_tilt_avg_deg': 12.5,
            'shoulder_tilt_exceed_ratio': 0.4,
            'head_down_avg_deg': 8.0,
            'head_down_exceed_ratio': 0.1,
            'gesture_activity_level': 'normal',
            'torso_signal_sufficient': true,
            'torso_lean_avg_deg': 5.0,
            'torso_lean_exceed_ratio': 0.2,
            'arm_openness_level': 'open',
            'reasons': ['어깨 기울어짐 40% 구간'],
          },
        ],
      },
    };

    final segments = mapper.buildSegments(result);

    expect(segments.length, 1);
    expect(segments.first.postureAvailable, true);
    expect(segments.first.postureSignalSufficient, true);
    expect(segments.first.shoulderTilt, '평균 12.5도 · 초과 40%');
    expect(segments.first.headDown, '평균 8.0도 · 초과 10%');
    expect(segments.first.torsoLean, '평균 5.0도 · 초과 20%');
    expect(segments.first.armOpenness, '열림');
    expect(segments.first.gestureActivity, '보통');
    expect(segments.first.postureReasons, ['어깨 기울어짐 40% 구간']);
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

  test('gestureActivityText and armOpennessText map known levels', () {
    expect(mapper.gestureActivityText('low'), '낮음');
    expect(mapper.gestureActivityText('normal'), '보통');
    expect(mapper.gestureActivityText('high'), '높음');
    expect(mapper.gestureActivityText('unknown'), '분석 없음');

    expect(mapper.armOpennessText('closed'), '닫힘');
    expect(mapper.armOpennessText('normal'), '보통');
    expect(mapper.armOpennessText('open'), '열림');
    expect(mapper.armOpennessText('unknown'), '분석 없음');
  });
}
