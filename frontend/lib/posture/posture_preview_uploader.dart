import 'dart:convert';

import 'package:http/http.dart' as http;

/// 녹화 중 실시간 반응(아바타 표정)용 짧은 주기 업로더.
/// `/posture/window`와 달리 세션/윈도우 인덱스 없이, 저장되지 않는
/// `/posture/preview`에 프레임을 보내 avatar_state만 빠르게 받아온다.
class PosturePreviewUploader {
  PosturePreviewUploader({
    required this.baseUrl,
    http.Client? client,
  }) : _client = client ?? http.Client();

  final String baseUrl;
  final http.Client _client;

  Future<Map<String, dynamic>> uploadPreview({
    required List<List<int>> frames,
  }) async {
    final uri = Uri.parse(baseUrl).replace(
      path: '/posture/preview',
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
        'posture preview upload failed: ${response.statusCode}',
      );
    }

    return jsonDecode(response.body) as Map<String, dynamic>;
  }
}
