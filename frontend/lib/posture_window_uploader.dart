import 'package:http/http.dart' as http;

class PostureWindowUploader {
  PostureWindowUploader({
    required this.baseUrl,
    required this.sessionId,
    http.Client? client,
  }) : _client = client ?? http.Client();

  final String baseUrl;
  final String sessionId;
  final http.Client _client;

  Future<void> uploadWindow({
    required int windowIndex,
    required List<List<int>> frames,
  }) async {
    final uri = Uri.parse(baseUrl).replace(
      path: '/posture/window',
      queryParameters: {
        'session_id': sessionId,
        'window_index': '$windowIndex',
      },
    );

    final request = http.MultipartRequest('POST', uri);

    for (var i = 0; i < frames.length; i++) {
      request.files.add(
        http.MultipartFile.fromBytes(
          'frames',
          frames[i],
          filename: 'frame_$i.jpg',
        ),
      );
    }

    final streamedResponse = await _client.send(request);
    final response = await http.Response.fromStream(streamedResponse);

    if (response.statusCode != 200) {
      throw Exception(
        'posture window upload failed: ${response.statusCode}',
      );
    }
  }
}
