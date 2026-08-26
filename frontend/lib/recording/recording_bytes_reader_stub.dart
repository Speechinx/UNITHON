import 'dart:io';
import 'dart:typed_data';

/// 네이티브(Android/iOS/desktop)에서는 record 패키지가 로컬 파일 경로를
/// 반환하므로, blob URL이 아니라 파일 시스템에서 직접 읽는다.
Future<Uint8List> readRecordingBytes(String path) async {
  final file = File(path);

  if (!await file.exists()) {
    throw Exception('녹음 파일을 불러오지 못했습니다.');
  }

  return file.readAsBytes();
}
