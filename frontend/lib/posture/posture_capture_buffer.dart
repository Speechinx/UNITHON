class PostureCaptureBuffer {
  final List<List<int>> _frames = [];

  void addFrame(List<int> jpegBytes) {
    _frames.add(jpegBytes);
  }

  List<List<int>> flush() {
    final frames = List<List<int>>.from(_frames);
    _frames.clear();
    return frames;
  }

  int get frameCount => _frames.length;
}
