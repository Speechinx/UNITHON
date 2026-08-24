import 'dart:html' as html;

void revokePostureFrameBlobUrl(String path) {
  try {
    html.Url.revokeObjectUrl(path);
  } catch (_) {}
}
