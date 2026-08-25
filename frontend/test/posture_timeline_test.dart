import 'package:flutter_test/flutter_test.dart';
import 'package:pr_front/posture/posture_timeline.dart';

void main() {
  test('fromJson parses all fields', () {
    final window = PostureWindow.fromJson({
      'window_index': 2,
      'signal_sufficient': true,
      'shoulder_tilt_exceed_ratio': 0.4,
      'head_down_exceed_ratio': 0.1,
      'gesture_activity_level': 'normal',
    });

    expect(window.windowIndex, 2);
    expect(window.signalSufficient, true);
    expect(window.shoulderTiltExceedRatio, 0.4);
    expect(window.headDownExceedRatio, 0.1);
    expect(window.gestureActivityLevel, 'normal');
  });

  test('fromJson defaults missing ratio fields to 0.0 and level to unknown', () {
    final window = PostureWindow.fromJson({
      'window_index': 0,
      'signal_sufficient': false,
    });

    expect(window.shoulderTiltExceedRatio, 0.0);
    expect(window.headDownExceedRatio, 0.0);
    expect(window.gestureActivityLevel, 'unknown');
  });

  test('fromJson parses shoulder/head avg degrees and reasons', () {
    final window = PostureWindow.fromJson({
      'window_index': 1,
      'signal_sufficient': true,
      'shoulder_tilt_avg_deg': 12.5,
      'shoulder_tilt_exceed_ratio': 0.4,
      'head_down_avg_deg': 65.0,
      'head_down_exceed_ratio': 0.1,
      'gesture_activity_level': 'normal',
      'reasons': ['어깨 기울어짐 40% 구간'],
    });

    expect(window.shoulderTiltAvgDeg, 12.5);
    expect(window.headDownAvgDeg, 65.0);
    expect(window.reasons, ['어깨 기울어짐 40% 구간']);
  });

  test(
    'fromJson defaults avg degree fields to 0.0 and reasons to empty list',
    () {
      final window = PostureWindow.fromJson({
        'window_index': 0,
        'signal_sufficient': false,
      });

      expect(window.shoulderTiltAvgDeg, 0.0);
      expect(window.headDownAvgDeg, 0.0);
      expect(window.reasons, <String>[]);
    },
  );

  test('fromJson parses torso lean and open posture fields', () {
    final window = PostureWindow.fromJson({
      'window_index': 1,
      'signal_sufficient': true,
      'torso_signal_sufficient': true,
      'torso_lean_avg_deg': 12.0,
      'torso_lean_exceed_ratio': 0.4,
      'torso_lean_level': 'mild',
      'torso_lean_direction': 'forward',
      'open_posture_level': 'open',
    });

    expect(window.torsoSignalSufficient, true);
    expect(window.torsoLeanAvgDeg, 12.0);
    expect(window.torsoLeanExceedRatio, 0.4);
    expect(window.torsoLeanLevel, 'mild');
    expect(window.torsoLeanDirection, 'forward');
    expect(window.openPostureLevel, 'open');
  });

  test(
    'fromJson defaults torso fields to insufficient and open posture to unknown',
    () {
      final window = PostureWindow.fromJson({
        'window_index': 0,
        'signal_sufficient': false,
      });

      expect(window.torsoSignalSufficient, false);
      expect(window.torsoLeanAvgDeg, 0.0);
      expect(window.torsoLeanExceedRatio, 0.0);
      expect(window.torsoLeanLevel, 'unknown');
      expect(window.torsoLeanDirection, 'unknown');
      expect(window.openPostureLevel, 'unknown');
    },
  );

  test('fromJson parses shoulder/head/gaze/sway levels', () {
    final window = PostureWindow.fromJson({
      'window_index': 0,
      'signal_sufficient': true,
      'shoulder_tilt_level': 'mild',
      'head_down_level': 'stable',
      'sway_level': 'severe',
      'gaze_away_level': 'mild',
    });

    expect(window.shoulderTiltLevel, 'mild');
    expect(window.headDownLevel, 'stable');
    expect(window.swayLevel, 'severe');
    expect(window.gazeAwayLevel, 'mild');
  });

  test('fromJson defaults new level fields to unknown', () {
    final window = PostureWindow.fromJson({
      'window_index': 0,
      'signal_sufficient': false,
    });

    expect(window.shoulderTiltLevel, 'unknown');
    expect(window.headDownLevel, 'unknown');
    expect(window.swayLevel, 'unknown');
    expect(window.gazeAwayLevel, 'unknown');
    expect(window.powerZoneLevel, 'unknown');
    expect(window.headAlignmentLevel, 'unknown');
  });

  test('fromJson parses power zone and head alignment levels', () {
    final window = PostureWindow.fromJson({
      'window_index': 0,
      'signal_sufficient': true,
      'power_zone_level': 'high',
      'head_alignment_level': 'severe',
    });

    expect(window.powerZoneLevel, 'high');
    expect(window.headAlignmentLevel, 'severe');
  });
}
