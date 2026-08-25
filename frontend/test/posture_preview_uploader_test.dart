import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:pr_front/posture/posture_preview_uploader.dart';

void main() {
  test('uploadPreview sends POST to the correct path with no query params', () async {
    Uri? capturedUri;
    String? capturedMethod;

    final mockClient = MockClient((request) async {
      capturedUri = request.url;
      capturedMethod = request.method;
      return http.Response('{}', 200);
    });

    final uploader = PosturePreviewUploader(
      baseUrl: 'http://127.0.0.1:8000',
      client: mockClient,
    );

    await uploader.uploadPreview(
      frames: [
        [1, 2, 3],
      ],
    );

    expect(capturedUri?.path, '/posture/preview');
    expect(capturedUri?.queryParameters, isEmpty);
    expect(capturedMethod, 'POST');
  });

  test('uploadPreview throws when server returns non-200', () async {
    final mockClient = MockClient((request) async {
      return http.Response('error', 500);
    });

    final uploader = PosturePreviewUploader(
      baseUrl: 'http://127.0.0.1:8000',
      client: mockClient,
    );

    expect(
      () => uploader.uploadPreview(
        frames: [
          [1, 2, 3],
        ],
      ),
      throwsException,
    );
  });

  test('uploadPreview returns the parsed JSON response body', () async {
    final mockClient = MockClient((request) async {
      return http.Response(
        '{"avatar_state": "focused"}',
        200,
      );
    });

    final uploader = PosturePreviewUploader(
      baseUrl: 'http://127.0.0.1:8000',
      client: mockClient,
    );

    final result = await uploader.uploadPreview(
      frames: [
        [1, 2, 3],
      ],
    );

    expect(result['avatar_state'], 'focused');
  });
}
