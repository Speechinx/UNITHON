import 'package:flutter_test/flutter_test.dart';
import 'package:pr_front/posture/posture_capture_buffer.dart';

void main() {
  test('addFrame increases frameCount', () {
    final buffer = PostureCaptureBuffer();

    buffer.addFrame([1, 2, 3]);

    expect(buffer.frameCount, 1);
  });

  test('flush returns accumulated frames and clears buffer', () {
    final buffer = PostureCaptureBuffer();

    buffer.addFrame([1, 2, 3]);
    buffer.addFrame([4, 5, 6]);

    final result = buffer.flush();

    expect(result, [
      [1, 2, 3],
      [4, 5, 6],
    ]);
    expect(buffer.frameCount, 0);
  });

  test('flush on empty buffer returns empty list', () {
    final buffer = PostureCaptureBuffer();

    expect(buffer.flush(), []);
  });
}
