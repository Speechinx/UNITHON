import 'dart:typed_data';

import 'package:http/http.dart' as http;

/// Flutter Web에서는 record 패키지가 녹음 파일을 blob:https://.../ 형태의
/// URL로 반환하므로, 그 blob을 fetch해서 바이트를 읽어야 한다.
Future<Uint8List> readRecordingBytes(String path) async {
  final response = await http.get(Uri.parse(path));

  if (response.statusCode != 200) {
    throw Exception('녹음 파일을 불러오지 못했습니다.');
  }

  return response.bodyBytes;
}
