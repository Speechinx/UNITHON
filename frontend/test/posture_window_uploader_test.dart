import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:pr_front/posture_window_uploader.dart';

void main() {
  test('uploadWindow sends POST to the correct path with query params', () async {
    Uri? capturedUri;
    String? capturedMethod;

    final mockClient = MockClient((request) async {
      capturedUri = request.url;
      capturedMethod = request.method;
      return http.Response('{}', 200);
    });

    final uploader = PostureWindowUploader(
      baseUrl: 'http://127.0.0.1:8000',
      sessionId: 'test-session',
      client: mockClient,
    );

    await uploader.uploadWindow(
      windowIndex: 3,
      frames: [
        [1, 2, 3],
      ],
    );

    expect(capturedUri?.path, '/posture/window');
    expect(capturedUri?.queryParameters['session_id'], 'test-session');
    expect(capturedUri?.queryParameters['window_index'], '3');
    expect(capturedMethod, 'POST');
  });

  test('uploadWindow throws when server returns non-200', () async {
    final mockClient = MockClient((request) async {
      return http.Response('error', 500);
    });

    final uploader = PostureWindowUploader(
      baseUrl: 'http://127.0.0.1:8000',
      sessionId: 'test-session',
      client: mockClient,
    );

    expect(
      () => uploader.uploadWindow(
        windowIndex: 0,
        frames: [
          [1, 2, 3],
        ],
      ),
      throwsException,
    );
  });

  test('uploadWindow returns the parsed JSON response body', () async {
    final mockClient = MockClient((request) async {
      return http.Response(
        '{"avatar_state": "good", "window_index": 3}',
        200,
      );
    });

    final uploader = PostureWindowUploader(
      baseUrl: 'http://127.0.0.1:8000',
      sessionId: 'test-session',
      client: mockClient,
    );

    final result = await uploader.uploadWindow(
      windowIndex: 3,
      frames: [
        [1, 2, 3],
      ],
    );

    expect(result['avatar_state'], 'good');
    expect(result['window_index'], 3);
  });
}
