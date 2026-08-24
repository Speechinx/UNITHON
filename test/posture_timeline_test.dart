import 'package:flutter_test/flutter_test.dart';
import 'package:pr_front/posture_timeline.dart';

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
}
