# Posture Tracking Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** During recording, capture sparse low-resolution webcam frames, buffer them into 15-second windows, and stream each window to the backend's `POST /posture/window` endpoint (see the backend plan, `pr_helper/docs/superpowers/plans/2026-08-24-posture-tracking-backend.md`), then render the resulting posture timeline on `ResultPage`.

**Architecture:** Two new pure-Dart classes (`PostureCaptureBuffer`, `PostureWindowUploader`) that are fully unit-testable without hardware, wired into the existing `_HomePageState` recording lifecycle in `lib/main.dart`. A new standalone `PostureTimeline` widget (own file, since `ResultPage`'s existing timeline widgets are private to `main.dart`) renders the result.

**Tech Stack:** Flutter Web, `camera` package (frame capture — this app targets Flutter Web, confirmed by the existing blob-URL handling in `stopRecording()`), `image` package (client-side resize), `http` (already a dependency).

## Global Constraints

- Do not modify the existing audio recording path (`record` package usage in `startRecording`/`stopRecording`) beyond adding calls to the new posture methods — it must keep working exactly as today if camera capture fails.
- Backend base URL stays `http://127.0.0.1:8000`, matching the existing hardcoded value in `analyzeWavBytes` — do not introduce a new shared constant (out of scope, unrelated refactor).
- Target frame size 320x240, JPEG quality 70, capture interval 300–500ms, matching the backend design doc.
- Posture capture failures (camera permission denied, upload failure) must never block or crash the audio recording/analysis flow — always fail silently and continue, matching the backend's "signal_sufficient: false" graceful degradation.

---

## File Structure

- `lib/posture_capture_buffer.dart` — new. Pure buffering logic, no Flutter/camera dependency.
- `lib/posture_window_uploader.dart` — new. HTTP upload logic, injectable `http.Client` for testing.
- `lib/posture_timeline.dart` — new. `PostureWindow` model + `PostureTimeline` widget.
- `lib/main.dart` — modified. Wire camera capture into `_HomePageState` (Task 3), wire `PostureTimeline` into `ResultPage` (Task 5).
- `pubspec.yaml` — modified. Add `camera` and `image` dependencies.
- `test/posture_capture_buffer_test.dart` — new.
- `test/posture_window_uploader_test.dart` — new.
- `test/posture_timeline_test.dart` — new.

---

### Task 1: PostureCaptureBuffer

**Files:**
- Create: `lib/posture_capture_buffer.dart`
- Create: `test/posture_capture_buffer_test.dart`

**Interfaces:**
- Produces: `PostureCaptureBuffer.addFrame(List<int> jpegBytes)`, `.flush() -> List<List<int>>`, `.frameCount -> int`. Consumed by Task 3.

- [ ] **Step 1: Write the failing test**

Create `test/posture_capture_buffer_test.dart`:

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:pr_front/posture_capture_buffer.dart';

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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `flutter test test/posture_capture_buffer_test.dart`
Expected: FAIL — `Error: Not found: 'package:pr_front/posture_capture_buffer.dart'`

- [ ] **Step 3: Write the implementation**

Create `lib/posture_capture_buffer.dart`:

```dart
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `flutter test test/posture_capture_buffer_test.dart`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add lib/posture_capture_buffer.dart test/posture_capture_buffer_test.dart
git commit -m "feat: add posture capture buffer"
```

---

### Task 2: PostureWindowUploader

**Files:**
- Modify: `pubspec.yaml` (no new dependency needed here — `http` already present)
- Create: `lib/posture_window_uploader.dart`
- Create: `test/posture_window_uploader_test.dart`

**Interfaces:**
- Consumes: `List<List<int>>` frames from `PostureCaptureBuffer.flush()` (Task 1).
- Produces: `PostureWindowUploader.uploadWindow({required int windowIndex, required List<List<int>> frames}) -> Future<void>`, throws on non-200. Consumed by Task 3.

- [ ] **Step 1: Write the failing test**

Create `test/posture_window_uploader_test.dart`:

```dart
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
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `flutter test test/posture_window_uploader_test.dart`
Expected: FAIL — `Error: Not found: 'package:pr_front/posture_window_uploader.dart'`

- [ ] **Step 3: Write the implementation**

Create `lib/posture_window_uploader.dart`:

```dart
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `flutter test test/posture_window_uploader_test.dart`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add lib/posture_window_uploader.dart test/posture_window_uploader_test.dart
git commit -m "feat: add posture window uploader"
```

---

### Task 3: Wire camera capture into `_HomePageState`

**Files:**
- Modify: `pubspec.yaml`
- Modify: `lib/main.dart`

**Interfaces:**
- Consumes: `PostureCaptureBuffer` (Task 1), `PostureWindowUploader` (Task 2).

This task has no automated test — `camera` requires real hardware/browser permissions. Verify manually in Step 8.

- [ ] **Step 1: Add dependencies**

Run:
```bash
flutter pub add camera
flutter pub add image
```
Expected: `pubspec.yaml` gains `camera: ^<version>` and `image: ^<version>` under `dependencies`.

- [ ] **Step 2: Add imports**

In `lib/main.dart`, add these imports near the top, alongside the existing `import 'package:record/record.dart';`:

```dart
import 'package:camera/camera.dart';
import 'package:image/image.dart' as img;

import 'posture_capture_buffer.dart';
import 'posture_window_uploader.dart';
```

- [ ] **Step 3: Add new fields to `_HomePageState`**

Find this existing line (near the top of `_HomePageState`, right after `final AudioRecorder _audioRecorder = AudioRecorder();`):

```dart
  final AudioRecorder _audioRecorder = AudioRecorder();
```

Add these fields directly after it:

```dart
  CameraController? _cameraController;
  final PostureCaptureBuffer _postureBuffer = PostureCaptureBuffer();
  Timer? _postureCaptureTimer;
  Timer? _postureFlushTimer;
  int _postureWindowIndex = 0;
  String? _postureSessionId;
  PostureWindowUploader? _postureUploader;
```

- [ ] **Step 4: Start posture capture from `startRecording()`**

Find this block inside `startRecording()` (right after the `_audioRecorder.start(...)` call succeeds):

```dart
    setState(() {
      isRecording = true;
      recordingSeconds = 0;
    });
```

Change it to also kick off posture capture (audio recording must keep working even if this fails, hence the nested try/catch):

```dart
    setState(() {
      isRecording = true;
      recordingSeconds = 0;
    });

    try {
      await _startPostureCapture();
    } catch (e) {
      debugPrint('자세 캡처를 시작하지 못했습니다: $e');
    }
```

Now add the new methods. Insert them right before `Future<void> stopRecording() async {`:

```dart
  Future<void> _startPostureCapture() async {
    _postureSessionId = DateTime.now().millisecondsSinceEpoch.toString();
    _postureWindowIndex = 0;

    _postureUploader = PostureWindowUploader(
      baseUrl: 'http://127.0.0.1:8000',
      sessionId: _postureSessionId!,
    );

    final cameras = await availableCameras();

    if (cameras.isEmpty) {
      return;
    }

    final frontCamera = cameras.firstWhere(
      (camera) => camera.lensDirection == CameraLensDirection.front,
      orElse: () => cameras.first,
    );

    _cameraController = CameraController(
      frontCamera,
      ResolutionPreset.low,
      enableAudio: false,
    );

    await _cameraController!.initialize();

    _postureCaptureTimer = Timer.periodic(
      const Duration(milliseconds: 400),
      (_) => _capturePostureFrame(),
    );

    _postureFlushTimer = Timer.periodic(
      const Duration(seconds: 15),
      (_) => _flushPostureWindow(),
    );
  }

  Future<void> _capturePostureFrame() async {
    final controller = _cameraController;

    if (controller == null || !controller.value.isInitialized) {
      return;
    }

    try {
      final file = await controller.takePicture();
      final bytes = await file.readAsBytes();
      final resized = _resizeJpeg(bytes);

      _postureBuffer.addFrame(resized);
    } catch (e) {
      debugPrint('자세 프레임 캡처 실패: $e');
    }
  }

  List<int> _resizeJpeg(List<int> originalBytes) {
    final decoded = img.decodeImage(originalBytes);

    if (decoded == null) {
      return originalBytes;
    }

    final resized = img.copyResize(decoded, width: 320, height: 240);

    return img.encodeJpg(resized, quality: 70);
  }

  Future<void> _flushPostureWindow() async {
    final frames = _postureBuffer.flush();
    final windowIndex = _postureWindowIndex;
    _postureWindowIndex += 1;

    if (frames.isEmpty || _postureUploader == null) {
      return;
    }

    try {
      await _postureUploader!.uploadWindow(
        windowIndex: windowIndex,
        frames: frames,
      );
    } catch (e) {
      debugPrint('자세 window 업로드 실패 (건너뜀): $e');
    }
  }

  Future<void> _stopPostureCapture() async {
    _postureCaptureTimer?.cancel();
    _postureFlushTimer?.cancel();

    await _flushPostureWindow();

    await _cameraController?.dispose();
    _cameraController = null;
  }

```

- [ ] **Step 5: Stop posture capture from `stopRecording()` and pass the session ID through**

Find this line inside `stopRecording()`:

```dart
    _recordingTimer?.cancel();

    final path = await _audioRecorder.stop();
```

Change it to:

```dart
    _recordingTimer?.cancel();

    await _stopPostureCapture();

    final path = await _audioRecorder.stop();
```

Then find this line (the call to `analyzeWavBytes` at the end of `stopRecording()`):

```dart
    // 기존 WAV 업로드와 동일한 분석 과정 사용
    await analyzeWavBytes(
      bytes,
      filename: 'recorded_presentation.wav',
    );
```

Change it to pass the session ID:

```dart
    // 기존 WAV 업로드와 동일한 분석 과정 사용
    await analyzeWavBytes(
      bytes,
      filename: 'recorded_presentation.wav',
      sessionId: _postureSessionId,
    );
```

- [ ] **Step 6: Accept the optional `sessionId` in `analyzeWavBytes` and thread it into the request URL**

Find:

```dart
  Future<void> analyzeWavBytes(
    Uint8List bytes, {
    String filename = 'presentation.wav',
  }) async {
```

Change it to:

```dart
  Future<void> analyzeWavBytes(
    Uint8List bytes, {
    String filename = 'presentation.wav',
    String? sessionId,
  }) async {
```

Find:

```dart
      final request = http.MultipartRequest(
        'POST',
        Uri.parse(
          'http://127.0.0.1:8000/analyze',
        ),
      );
```

Change it to:

```dart
      final analyzeUri = Uri.parse(
        'http://127.0.0.1:8000/analyze',
      ).replace(
        queryParameters: sessionId == null
            ? null
            : {'session_id': sessionId},
      );

      final request = http.MultipartRequest(
        'POST',
        analyzeUri,
      );
```

Note: `pickAndAnalyzeWav()` (the file-upload path) calls `analyzeWavBytes` without a `sessionId` — leave that call unchanged, so uploaded files never carry posture data (there's nothing to attach; posture requires a live recording).

- [ ] **Step 7: Clean up in `dispose()`**

Find:

```dart
  @override
  void dispose() {
    _recordingTimer?.cancel();
    _audioRecorder.dispose();

    super.dispose();
  }
```

Change it to:

```dart
  @override
  void dispose() {
    _recordingTimer?.cancel();
    _audioRecorder.dispose();

    _postureCaptureTimer?.cancel();
    _postureFlushTimer?.cancel();
    _cameraController?.dispose();

    super.dispose();
  }
```

- [ ] **Step 8: Manual verification**

Run: `flutter run -d chrome`

1. Grant microphone AND camera permission when prompted.
2. Start a recording, wait at least 20 seconds (so at least one 15-second flush fires), stop recording.
3. In the browser console / `flutter run` terminal, confirm you see no `자세 window 업로드 실패` messages, and that the debug prints show frames being captured.
4. Separately, run the backend (`uvicorn app.main:app --reload` in `pr_helper`) and confirm in its logs that `POST /posture/window` requests arrive during recording.
5. Confirm the existing "파일 업로드" (pickAndAnalyzeWav) path still works unaffected — it should not attempt any camera access.

- [ ] **Step 9: Commit**

```bash
git add pubspec.yaml pubspec.lock lib/main.dart
git commit -m "feat: capture and stream posture frames during recording"
```

---

### Task 4: PostureTimeline widget

**Files:**
- Create: `lib/posture_timeline.dart`
- Create: `test/posture_timeline_test.dart`

**Interfaces:**
- Consumes: JSON matching the backend's `PostureWindow` schema (`pr_helper` Task 5): `window_index`, `signal_sufficient`, `shoulder_tilt_exceed_ratio`, `head_down_exceed_ratio`, `gesture_activity_level`.
- Produces: `PostureWindow.fromJson(Map<String, dynamic>) -> PostureWindow`, `PostureTimeline({required List<PostureWindow> windows})` widget. Consumed by Task 5.

- [ ] **Step 1: Write the failing tests**

Create `test/posture_timeline_test.dart`:

```dart
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `flutter test test/posture_timeline_test.dart`
Expected: FAIL — `Error: Not found: 'package:pr_front/posture_timeline.dart'`

- [ ] **Step 3: Write the implementation**

Create `lib/posture_timeline.dart`:

```dart
import 'package:flutter/material.dart';

class PostureWindow {
  const PostureWindow({
    required this.windowIndex,
    required this.signalSufficient,
    required this.shoulderTiltExceedRatio,
    required this.headDownExceedRatio,
    required this.gestureActivityLevel,
  });

  final int windowIndex;
  final bool signalSufficient;
  final double shoulderTiltExceedRatio;
  final double headDownExceedRatio;
  final String gestureActivityLevel;

  factory PostureWindow.fromJson(Map<String, dynamic> json) {
    return PostureWindow(
      windowIndex: json['window_index'] as int,
      signalSufficient: json['signal_sufficient'] as bool? ?? false,
      shoulderTiltExceedRatio:
          (json['shoulder_tilt_exceed_ratio'] as num?)?.toDouble() ?? 0.0,
      headDownExceedRatio:
          (json['head_down_exceed_ratio'] as num?)?.toDouble() ?? 0.0,
      gestureActivityLevel:
          json['gesture_activity_level'] as String? ?? 'unknown',
    );
  }
}

class PostureTimeline extends StatelessWidget {
  const PostureTimeline({
    super.key,
    required this.windows,
  });

  final List<PostureWindow> windows;

  @override
  Widget build(BuildContext context) {
    if (windows.isEmpty) {
      return const SizedBox.shrink();
    }

    return SizedBox(
      height: 64,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: windows.length,
        separatorBuilder: (_, __) => const SizedBox(width: 4),
        itemBuilder: (context, index) {
          return _PostureWindowChip(window: windows[index]);
        },
      ),
    );
  }
}

class _PostureWindowChip extends StatelessWidget {
  const _PostureWindowChip({required this.window});

  final PostureWindow window;

  Color _colorFor(PostureWindow window) {
    if (!window.signalSufficient) {
      return Colors.grey.shade300;
    }

    final risk = window.shoulderTiltExceedRatio + window.headDownExceedRatio;

    if (risk >= 0.6) {
      return Colors.red.shade300;
    }

    if (risk >= 0.3) {
      return Colors.orange.shade300;
    }

    return Colors.green.shade300;
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 40,
      decoration: BoxDecoration(
        color: _colorFor(window),
        borderRadius: BorderRadius.circular(8),
      ),
      alignment: Alignment.center,
      child: Text(
        '${window.windowIndex}',
        style: const TextStyle(fontSize: 12),
      ),
    );
  }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `flutter test test/posture_timeline_test.dart`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add lib/posture_timeline.dart test/posture_timeline_test.dart
git commit -m "feat: add posture timeline widget"
```

---

### Task 5: Wire `PostureTimeline` into `ResultPage`

**Files:**
- Modify: `lib/main.dart`

**Interfaces:**
- Consumes: `PostureWindow`, `PostureTimeline` (Task 4); `result['posture']['windows']` from the `/analyze` JSON response (backend plan Task 5/7).

No automated test — this is a rendering wire-up. Verify manually in Step 4.

- [ ] **Step 1: Import the new widget**

Add near the top of `lib/main.dart`:

```dart
import 'posture_timeline.dart';
```

- [ ] **Step 2: Parse posture windows in `_ResultPageState`**

`ResultPage` receives `result` as a `Map<String, dynamic>` (see the `ResultPage(result: decoded)` call site in `analyzeWavBytes`). In `_ResultPageState` (the class starting at the line `class _ResultPageState extends State<ResultPage> {`), add a getter that parses the posture windows from `widget.result`:

```dart
  List<PostureWindow> get _postureWindows {
    final posture = widget.result['posture'];

    if (posture is! Map<String, dynamic>) {
      return [];
    }

    final windows = posture['windows'];

    if (windows is! List) {
      return [];
    }

    return windows
        .whereType<Map<String, dynamic>>()
        .map(PostureWindow.fromJson)
        .toList();
  }
```

(If the existing class stores the incoming map under a different field name than `widget.result`, use that field name instead — check the `ResultPage` constructor's `result` parameter and how `_ResultPageState` already reads other top-level keys like `risk` or `coaching`, and match that exact access pattern.)

- [ ] **Step 3: Render the timeline**

In `_ResultPageState.build()`, find where the existing voice risk timeline section is rendered (search for where `_RiskTimeline(` is instantiated) and add the posture timeline as a sibling section right after it, using the same `_SectionCard` wrapper the rest of the page uses for consistency:

```dart
              _SectionCard(
                title: '자세 타임라인',
                child: PostureTimeline(
                  windows: _postureWindows,
                ),
              ),
```

(Match `_SectionCard`'s actual constructor parameters — check its definition, since this plan was written without seeing every call site. If `_SectionCard` requires additional parameters, add them consistently with neighboring usages.)

- [ ] **Step 4: Manual verification**

Run: `flutter run -d chrome`, record a presentation for 20+ seconds with backend Task 7 deployed, and confirm colored posture chips appear on the result screen. Record a presentation shorter than 15 seconds and confirm the section renders nothing (empty state) rather than crashing.

- [ ] **Step 5: Commit**

```bash
git add lib/main.dart
git commit -m "feat: render posture timeline on result page"
```

---

## Self-Review Notes

- **Spec coverage**: camera capture cadence (300–500ms → used 400ms), 320x240/quality 70 resize, 15-second flush, silent-skip-on-failure are all covered (Task 3). The posture timeline visualization is covered (Task 4–5).
- **Type consistency**: `PostureWindow.fromJson` field names match exactly what the backend plan's `PostureWindow` Pydantic model serializes to (snake_case JSON keys), and `PostureWindowUploader`'s query param names (`session_id`, `window_index`) match the backend's `POST /posture/window` and `POST /analyze` query parameter names exactly.
- **Known gap flagged for manual handling**: Task 5 Steps 2–3 depend on `ResultPage`/`_SectionCard`'s exact existing structure, which this plan could not fully inspect (main.dart is 2389 lines). The implementer must read the actual `_ResultPageState` and `_SectionCard` source before applying Task 5 — this is called out explicitly in the task rather than guessed.
