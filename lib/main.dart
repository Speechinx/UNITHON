import 'dart:convert';

import 'dart:ui' show PointerDeviceKind;

import 'dart:async';
import 'package:record/record.dart';
import 'package:camera/camera.dart';
import 'package:image/image.dart' as img;

import 'posture_capture_buffer.dart';
import 'posture_window_uploader.dart';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;


void main() {
  runApp(
    const PresentationCoachApp(),
  );
}


// ============================================================
// APP
// ============================================================

class PresentationCoachApp extends StatelessWidget {
  const PresentationCoachApp({
    super.key,
  });

  @override
  Widget build(
    BuildContext context,
  ) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'AI Presentation Coach',

      scrollBehavior:
          const MaterialScrollBehavior().copyWith(
        dragDevices: {
          PointerDeviceKind.touch,
          PointerDeviceKind.mouse,
          PointerDeviceKind.trackpad,
          PointerDeviceKind.stylus,
        },
      ),

      theme: ThemeData(
        useMaterial3: true,
        scaffoldBackgroundColor:
            const Color(0xFFF5F6F8),
      ),

      home: const HomePage(),
    );
  }
}


// ============================================================
// HOME PAGE
// ============================================================

class HomePage extends StatefulWidget {
  const HomePage({
    super.key,
  });

  @override
  State<HomePage> createState() {
    return _HomePageState();
  }
}


class _HomePageState extends State<HomePage> {
  final AudioRecorder _audioRecorder = AudioRecorder();
  CameraController? _cameraController;
  final PostureCaptureBuffer _postureBuffer = PostureCaptureBuffer();
  Timer? _postureCaptureTimer;
  Timer? _postureFlushTimer;
  int _postureWindowIndex = 0;
  String? _postureSessionId;
  PostureWindowUploader? _postureUploader;

  bool isRecording = false;
  int recordingSeconds = 0;

  Timer? _recordingTimer;

  Future<void> startRecording() async {
  if (isLoading || isRecording) {
    return;
  }

  try {
    setState(() {
      errorMessage = null;
    });

    final hasPermission =
        await _audioRecorder.hasPermission();

    if (!hasPermission) {
      setState(() {
        errorMessage = '마이크 권한을 허용해주세요.';
      });
      return;
    }

    await _audioRecorder.start(
      const RecordConfig(
        encoder: AudioEncoder.wav,
        sampleRate: 16000,
        numChannels: 1,
        echoCancel: true,
        noiseSuppress: true,
        autoGain: true,
      ),
      path: 'presentation.wav',
    );

    setState(() {
      isRecording = true;
      recordingSeconds = 0;
    });

    try {
      await _startPostureCapture();
    } catch (e) {
      debugPrint('자세 캡처를 시작하지 못했습니다: $e');
    }

    _recordingTimer?.cancel();

    _recordingTimer = Timer.periodic(
      const Duration(seconds: 1),
      (_) {
        if (!mounted) {
          return;
        }

        setState(() {
          recordingSeconds++;
        });
      },
    );
  } catch (e) {
    if (!mounted) {
      return;
    }

    setState(() {
      errorMessage = '녹음을 시작할 수 없습니다: $e';
    });
  }
}

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

  List<int> _resizeJpeg(Uint8List originalBytes) {
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

Future<void> stopRecording() async {
  if (!isRecording) {
    return;
  }

  try {
    _recordingTimer?.cancel();

    await _stopPostureCapture();

    final path = await _audioRecorder.stop();

    if (!mounted) {
      return;
    }

    setState(() {
      isRecording = false;
    });

    if (path == null) {
      throw Exception(
        '녹음 파일을 생성하지 못했습니다.',
      );
    }

    debugPrint(
      '녹음 파일 경로: $path',
    );

    // Flutter Web에서는 녹음 파일이
    // blob:http://localhost:5173/... 형태로 반환됨
    final blobResponse = await http.get(
      Uri.parse(path),
    );

    if (blobResponse.statusCode != 200) {
      throw Exception(
        '녹음 파일을 불러오지 못했습니다.',
      );
    }

    final bytes = blobResponse.bodyBytes;

    if (bytes.isEmpty) {
      throw Exception(
        '녹음된 오디오가 비어 있습니다.',
      );
    }

    debugPrint(
      '녹음 WAV 크기: ${bytes.length} bytes',
    );

    // 기존 WAV 업로드와 동일한 분석 과정 사용
    await analyzeWavBytes(
      bytes,
      filename: 'recorded_presentation.wav',
      sessionId: _postureSessionId,
    );
  } catch (e) {
    if (!mounted) {
      return;
    }

    setState(() {
      isRecording = false;

      errorMessage = e
          .toString()
          .replaceFirst(
            'Exception: ',
            '',
          );
    });
  }
}


String formatRecordingTime(
  int seconds,
) {
  final minutes = seconds ~/ 60;
  final remainingSeconds = seconds % 60;

  return '${minutes.toString().padLeft(2, '0')}:'
      '${remainingSeconds.toString().padLeft(2, '0')}';
}

  bool isLoading = false;

  String? errorMessage;


  Future<void> analyzeWavBytes(
    Uint8List bytes, {
    String filename = 'presentation.wav',
    String? sessionId,
  }) async {
    setState(() {
      isLoading = true;
      errorMessage = null;
    });

    try {
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

      request.files.add(
        http.MultipartFile.fromBytes(
          'file',
          bytes,
          filename: filename,
        ),
      );

      final streamedResponse =
          await request.send();

      final response =
          await http.Response.fromStream(
        streamedResponse,
      );

      if (response.statusCode != 200) {
        String detail =
            '분석 중 오류가 발생했습니다.';

        try {
          final errorJson =
              jsonDecode(
            utf8.decode(
              response.bodyBytes,
            ),
          );

          if (
              errorJson is Map &&
              errorJson['detail'] != null
          ) {
            detail =
                errorJson['detail'].toString();
          }
        } catch (_) {}

        throw Exception(detail);
      }

      final decoded =
          jsonDecode(
        utf8.decode(
          response.bodyBytes,
        ),
      );

      if (decoded is! Map<String, dynamic>) {
        throw Exception(
          '서버 응답 형식이 올바르지 않습니다.',
        );
      }

      if (!mounted) {
        return;
      }

      Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) {
            return ResultPage(
              result: decoded,
            );
          },
        ),
      );
    } catch (e) {
      if (!mounted) {
        return;
      }

      setState(() {
        errorMessage = e
            .toString()
            .replaceFirst(
              'Exception: ',
              '',
            );
      });
    } finally {
      if (mounted) {
        setState(() {
          isLoading = false;
        });
      }
    }
  }


  Future<void> pickAndAnalyzeWav() async {
    setState(() {
      errorMessage = null;
    });

    final file = await FilePicker.pickFile(
      type: FileType.custom,
      allowedExtensions: [
        'wav',
      ],
    );

    if (file == null) {
      return;
    }

    try {
      final bytes =
          await file.xFile.readAsBytes();

      await analyzeWavBytes(
        bytes,
        filename: file.name,
      );
    } catch (e) {
      if (!mounted) {
        return;
      }

      setState(() {
        errorMessage = e
            .toString()
            .replaceFirst(
              'Exception: ',
              '',
            );
      });
    }
  }

  @override
  void dispose() {
    _recordingTimer?.cancel();
    _audioRecorder.dispose();

    _postureCaptureTimer?.cancel();
    _postureFlushTimer?.cancel();
    _cameraController?.dispose();

    super.dispose();
  }

  @override
  Widget build(
    BuildContext context,
  ) {
    return Scaffold(
      body: Center(
        child: Container(
          width: double.infinity,
          constraints:
              const BoxConstraints(
            maxWidth: 430,
          ),
          color: Colors.white,
          child: SafeArea(
            child: Padding(
              padding:
                  const EdgeInsets.symmetric(
                horizontal: 24,
                vertical: 24,
              ),
              child: Column(
                crossAxisAlignment:
                    CrossAxisAlignment.start,
                children: [
                  const Text(
                    'AI Presentation Coach',
                    style: TextStyle(
                      fontSize: 28,
                      fontWeight:
                          FontWeight.bold,
                    ),
                  ),

                  const SizedBox(
                    height: 8,
                  ),

                  const Text(
                    '발표를 녹음하고 AI 피드백을 받아보세요.',
                    style: TextStyle(
                      fontSize: 15,
                      color:
                          Colors.black54,
                    ),
                  ),

                  const Spacer(),

                  Center(
                    child: Material(
                      color: Colors.transparent,
                      child: InkWell(
                        onTap: isLoading
                          ? null
                          : () {
                              if (isRecording) {
                                stopRecording();
                              } else {
                                startRecording();
                              }
                            },
                        customBorder: const CircleBorder(),
                        child: Ink(
                          width: 180,
                          height: 180,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: isRecording
                                ? Colors.red.shade50
                                : Colors.grey.shade100,
                          ),
                          child: Icon(
                            isRecording
                                ? Icons.stop_rounded
                                : Icons.mic_rounded,
                            size: 80,
                            color: isRecording
                                ? Colors.red.shade700
                                : Colors.black87,
                          ),
                        ),
                      ),
                    ),
                  ),

                  const SizedBox(
                    height: 28,
                  ),

                  Center(
                    child: Text(
                      isRecording
                          ? '녹음 중입니다'
                          : '발표 준비가 되셨나요?',
                      style: const TextStyle(
                        fontSize: 22,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),

                  const SizedBox(
                    height: 10,
                  ),

                  Center(
                    child: Text(
                      isRecording
                          ? formatRecordingTime(
                              recordingSeconds,
                            )
                          : '마이크 버튼을 눌러 녹음을 시작하거나\n'
                              'WAV 파일을 업로드해 발표 습관을 분석해보세요.',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        fontSize:
                            isRecording ? 18 : 15,
                        height: 1.5,
                        color: isRecording
                            ? Colors.red.shade700
                            : Colors.black54,
                        fontWeight: isRecording
                            ? FontWeight.w600
                            : FontWeight.normal,
                      ),
                    ),
                  ),

                  const SizedBox(
                    height: 28,
                  ),

                  if (
                      errorMessage != null
                  ) ...[
                    const SizedBox(
                      height: 20,
                    ),

                    Container(
                      width:
                          double.infinity,
                      padding:
                          const EdgeInsets.all(
                        14,
                      ),
                      decoration:
                          BoxDecoration(
                        color:
                            Colors.red.shade50,
                        borderRadius:
                            BorderRadius.circular(
                          12,
                        ),
                      ),
                      child: Text(
                        errorMessage!,
                        style:
                            TextStyle(
                          color:
                              Colors.red.shade700,
                        ),
                      ),
                    ),
                  ],

                  const Spacer(),

                  Padding(
                    padding: const EdgeInsets.only(
                      bottom: 28,
                    ),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        SizedBox(
                          width: double.infinity,
                          height: 52,
                          child: OutlinedButton.icon(
                            onPressed: isLoading
                                ? null
                                : pickAndAnalyzeWav,
                            icon: const Icon(
                              Icons.upload_file,
                            ),
                            label: const Text(
                              'WAV 파일 업로드',
                              style: TextStyle(
                                fontSize: 16,
                              ),
                            ),
                          ),
                        ),

                        if (isLoading) ...[
                          const SizedBox(
                            height: 20,
                          ),

                          const Center(
                            child: Column(
                              children: [
                                CircularProgressIndicator(),

                                SizedBox(
                                  height: 12,
                                ),

                                Text(
                                  '발표를 분석하고 있습니다...',
                                  style: TextStyle(
                                    color: Colors.black54,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}


// ============================================================
// RESULT PAGE
// ============================================================

class ResultPage extends StatefulWidget {
  final Map<String, dynamic> result;

  const ResultPage({
    super.key,
    required this.result,
  });

  @override
  State<ResultPage> createState() {
    return _ResultPageState();
  }
}


class _ResultPageState extends State<ResultPage> {
  int selectedWindowIndex = 0;

  bool showDetails = false;

  @override
  Widget build(
    BuildContext context,
  ) {
    final result =
        widget.result;

    final speech =
        Map<String, dynamic>.from(
      result['speech'] ?? {},
    );

    final risk =
        Map<String, dynamic>.from(
      result['risk'] ?? {},
    );

    final coaching =
        Map<String, dynamic>.from(
      result['coaching'] ?? {},
    );

    final fillers =
        List<Map<String, dynamic>>.from(
      (result['fillers'] ?? []).map(
        (item) =>
            Map<String, dynamic>.from(
          item,
        ),
      ),
    );

    final heatmap =
        List<Map<String, dynamic>>.from(
      (risk['heatmap'] ?? []).map(
        (item) =>
            Map<String, dynamic>.from(
          item,
        ),
      ),
    );

    final improvements =
        List<Map<String, dynamic>>.from(
      (coaching['improvements'] ?? [])
          .map(
        (item) =>
            Map<String, dynamic>.from(
          item,
        ),
      ),
    );

    final strengths =
        List<String>.from(
      coaching['strengths'] ?? [],
    );

    final practiceGoals =
        List<String>.from(
      coaching['practice_goals'] ?? [],
    );

    final fillerCount =
        fillers
            .where(
              (item) =>
                  item['type'] ==
                  'filler',
            )
            .length;

    final repetitionCount =
        fillers
            .where(
              (item) =>
                  item['type'] ==
                  'repetition',
            )
            .length;

    Map<String, dynamic>?
        selectedWindow;

    if (
        heatmap.isNotEmpty
    ) {
      if (
          selectedWindowIndex >=
          heatmap.length
      ) {
        selectedWindowIndex = 0;
      }

      selectedWindow =
          heatmap[
              selectedWindowIndex];
    }

    return Scaffold(
      body: Center(
        child: Container(
          width:
              double.infinity,
          constraints:
              const BoxConstraints(
            maxWidth: 430,
          ),
          color:
              Colors.white,
          child:
              SafeArea(
            child: Column(
              children: [
                _buildHeader(
                  context,
                ),

                Expanded(
                  child:
                      SingleChildScrollView(
                    padding:
                        const EdgeInsets.fromLTRB(
                      20,
                      8,
                      20,
                      36,
                    ),
                    child:
                        Column(
                      crossAxisAlignment:
                          CrossAxisAlignment.start,
                      children: [
                        // ==================================================
                        // AI 종합 평가
                        // ==================================================

                        _SectionCard(
                          title: 'AI 종합 평가',

                          trailing: _OverallStatusBadge(
                            level: risk['overall_level']
                                    ?.toString() ??
                                'low',
                          ),

                          child: Text(
                            coaching['summary']
                                    ?.toString() ??
                                '',
                            style: const TextStyle(
                              fontSize: 15,
                              height: 1.55,
                            ),
                          ),
                        ),

                        const SizedBox(
                          height: 16,
                        ),

                        // ==================================================
                        // 주요 지표
                        // ==================================================

                        Row(
                          children: [
                            Expanded(
                              child:
                                  _MetricCard(
                                title:
                                    '발표 속도',
                                value:
                                    _paceText(
                                  speech['pace_level']
                                      ?.toString(),
                                ),
                                subtitle:
                                    '${speech['presentation_rate'] ?? 0} 어절/분',
                              ),
                            ),

                            const SizedBox(
                              width: 12,
                            ),

                            Expanded(
                              child:
                                  _MetricCard(
                                title:
                                    '멈춤 비율',
                                value:
                                    '${_pausePercent(
                                  speech[
                                      'internal_pause_ratio'],
                                )}%',
                                subtitle:
                                    '총 ${speech['internal_pause_time'] ?? 0}초',
                              ),
                            ),
                          ],
                        ),

                        const SizedBox(
                          height: 12,
                        ),

                        Row(
                          children: [
                            Expanded(
                              child:
                                  _MetricCard(
                                title:
                                    '추임새',
                                value:
                                    '$fillerCount회',
                              ),
                            ),

                            const SizedBox(
                              width: 12,
                            ),

                            Expanded(
                              child:
                                  _MetricCard(
                                title:
                                    '반복',
                                value:
                                    '$repetitionCount회',
                              ),
                            ),
                          ],
                        ),

                        const SizedBox(
                          height: 20,
                        ),

                        SizedBox(
                          width: double.infinity,
                          height: 52,
                          child: OutlinedButton(
                            onPressed: () {
                              setState(() {
                                showDetails =
                                    !showDetails;
                              });
                            },

                            style:
                                OutlinedButton.styleFrom(
                              shape:
                                  RoundedRectangleBorder(
                                borderRadius:
                                    BorderRadius.circular(
                                  14,
                                ),
                              ),
                            ),

                            child: Row(
                              mainAxisAlignment:
                                  MainAxisAlignment.center,
                              children: [
                                Text(
                                  showDetails
                                      ? '상세 닫기'
                                      : '상세 보기',
                                  style:
                                      const TextStyle(
                                    fontSize: 15,
                                    fontWeight:
                                        FontWeight.w600,
                                  ),
                                ),

                                const SizedBox(
                                  width: 6,
                                ),

                                Icon(
                                  showDetails
                                      ? Icons
                                          .keyboard_arrow_up
                                      : Icons
                                          .keyboard_arrow_down,
                                ),
                              ],
                            ),
                          ),
                        ),

                        const SizedBox(
                          height: 16,
                        ),

                        // ==================================================
                        // 발표 흐름 타임라인
                        // ==================================================
                        if (showDetails) ...[
                        _SectionCard(
                          title:
                              '발표 흐름',
                          child:
                              Column(
                            crossAxisAlignment:
                                CrossAxisAlignment.start,
                            children: [
                              const Text(
                                '색이 진할수록 개선이 필요한 신호가 많이 탐지된 구간입니다.',
                                style:
                                    TextStyle(
                                  fontSize:
                                      12,
                                  color:
                                      Colors.black54,
                                  height:
                                      1.4,
                                ),
                              ),

                              const SizedBox(
                                height: 16,
                              ),

                              if (
                                  heatmap.isEmpty
                              )
                                const Text(
                                  '구간 분석 결과가 없습니다.',
                                )
                              else
                                _RiskTimeline(
                                  heatmap:
                                      heatmap,
                                  selectedIndex:
                                      selectedWindowIndex,
                                  onSelected:
                                      (
                                    index,
                                  ) {
                                    setState(() {
                                      selectedWindowIndex =
                                          index;
                                    });
                                  },
                                ),
                            ],
                          ),
                        ),

                        if (
                            selectedWindow !=
                            null
                        ) ...[
                          const SizedBox(
                            height: 16,
                          ),

                          // ==================================================
                          // 선택 구간 상세
                          // ==================================================

                          _WindowDetailCard(
                            window:
                                selectedWindow,
                          ),
                        ],

                        const SizedBox(
                          height: 16,
                        ),

                        // ==================================================
                        // 개선할 점
                        // ==================================================
                        _SectionCard(
                          title:
                              '개선할 점',
                          child:
                              Column(
                            crossAxisAlignment:
                                CrossAxisAlignment.start,
                            children:
                                improvements
                                    .asMap()
                                    .entries
                                    .map(
                              (
                                entry,
                              ) {
                                final index =
                                    entry.key;

                                final item =
                                    entry.value;

                                return Padding(
                                  padding:
                                      EdgeInsets.only(
                                    bottom:
                                        index ==
                                                improvements.length -
                                                    1
                                            ? 0
                                            : 18,
                                  ),
                                  child:
                                      Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        '${index + 1}. ${item['title'] ?? ''}',
                                        style:
                                            const TextStyle(
                                          fontSize:
                                              16,
                                          fontWeight:
                                              FontWeight.w600,
                                        ),
                                      ),

                                      if ((item[
                                                  'time_range'] ??
                                              '')
                                          .toString()
                                          .isNotEmpty) ...[
                                        const SizedBox(
                                          height:
                                              4,
                                        ),

                                        Text(
                                          item[
                                                  'time_range']
                                              .toString(),
                                          style:
                                              const TextStyle(
                                            fontSize:
                                                13,
                                            color:
                                                Colors.black45,
                                          ),
                                        ),
                                      ],

                                      const SizedBox(
                                        height:
                                            6,
                                      ),

                                      Text(
                                        item[
                                                    'description']
                                                ?.toString() ??
                                            '',
                                        style:
                                            const TextStyle(
                                          fontSize:
                                              14,
                                          height:
                                              1.5,
                                        ),
                                      ),
                                    ],
                                  ),
                                );
                              },
                            ).toList(),
                          ),
                        ),

                        const SizedBox(
                          height: 16,
                        ),

                        // ==================================================
                        // 연습 목표
                        // ==================================================

                        _SectionCard(
                          title:
                              '다음 연습 목표',
                          child:
                              Column(
                            crossAxisAlignment:
                                CrossAxisAlignment.start,
                            children:
                                practiceGoals
                                    .asMap()
                                    .entries
                                    .map(
                              (
                                entry,
                              ) {
                                return Padding(
                                  padding:
                                      const EdgeInsets.only(
                                    bottom:
                                        10,
                                  ),
                                  child:
                                      Text(
                                    '${entry.key + 1}. ${entry.value}',
                                    style:
                                        const TextStyle(
                                      fontSize:
                                          14,
                                      height:
                                          1.45,
                                    ),
                                  ),
                                );
                              },
                            ).toList(),
                          ),
                        ),

                        const SizedBox(
                          height: 16,
                        ),

                        // ==================================================
                        // 잘한 점
                        // ==================================================

                        _SectionCard(
                          title:
                              '잘한 점',
                          child:
                              Column(
                            crossAxisAlignment:
                                CrossAxisAlignment.start,
                            children:
                                strengths.map(
                              (
                                item,
                              ) {
                                return Padding(
                                  padding:
                                      const EdgeInsets.only(
                                    bottom:
                                        8,
                                  ),
                                  child:
                                      Text(
                                    '• $item',
                                    style:
                                        const TextStyle(
                                      fontSize:
                                          14,
                                      height:
                                          1.45,
                                    ),
                                  ),
                                );
                              },
                            ).toList(),
                          ),
                        ),

                        const SizedBox(
                          height: 16,
                        ),

                        // ==================================================
                        // 한 줄 코칭
                        // ==================================================

                        _SectionCard(
                          title:
                              '한 줄 코칭',
                          child:
                              Text(
                            coaching[
                                        'one_line_coaching']
                                    ?.toString() ??
                                '',
                            style:
                                const TextStyle(
                              fontSize:
                                  16,
                              height:
                                  1.5,
                              fontWeight:
                                  FontWeight.w600,
                            ),
                          ),
                        ),

                        const SizedBox(
                          height: 16,
                        ),

                        // ==================================================
                        // STT
                        // ==================================================

                        _SectionCard(
                          title: '발표 내용',

                          trailing: TextButton.icon(
                            onPressed: () async {
                              final transcript =
                                  result['transcript']
                                          ?.toString() ??
                                      '';

                              if (transcript.isEmpty) {
                                return;
                              }

                              await Clipboard.setData(
                                ClipboardData(
                                  text: transcript,
                                ),
                              );

                              if (!context.mounted) {
                                return;
                              }

                              ScaffoldMessenger.of(
                                context,
                              ).showSnackBar(
                                const SnackBar(
                                  content: Text(
                                    '발표 내용이 복사되었습니다.',
                                  ),
                                  duration: Duration(
                                    seconds: 2,
                                  ),
                                ),
                              );
                            },

                            icon: const Icon(
                              Icons.copy_rounded,
                              size: 17,
                            ),

                            label: const Text(
                              '복사',
                            ),
                          ),

                          child: Text(
                            result['transcript']
                                    ?.toString() ??
                                '',
                            style: const TextStyle(
                              fontSize: 14,
                              height: 1.55,
                            ),
                          ),
                        ),
                      ],],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }


  Widget _buildHeader(
    BuildContext context,
  ) {
    return Padding(
      padding:
          const EdgeInsets.fromLTRB(
        12,
        12,
        20,
        8,
      ),
      child:
          Row(
        children: [
          IconButton(
            onPressed: () {
              Navigator.of(
                context,
              ).pop();
            },
            icon:
                const Icon(
              Icons.arrow_back,
            ),
          ),

          const SizedBox(
            width: 4,
          ),

          const Text(
            '발표 분석 결과',
            style:
                TextStyle(
              fontSize:
                  22,
              fontWeight:
                  FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }
}


// ============================================================
// TIMELINE
// ============================================================

class _RiskTimeline extends StatelessWidget {
  final List<Map<String, dynamic>>
      heatmap;

  final int selectedIndex;

  final ValueChanged<int>
      onSelected;


  const _RiskTimeline({
    required this.heatmap,
    required this.selectedIndex,
    required this.onSelected,
  });


  @override
  Widget build(
    BuildContext context,
  ) {
    return SingleChildScrollView(
      scrollDirection:
          Axis.horizontal,
      child:
          Row(
        crossAxisAlignment:
            CrossAxisAlignment.start,
        children:
            List.generate(
          heatmap.length,
          (
            index,
          ) {
            final window =
                heatmap[index];

            final start =
                _asDouble(
              window['start'],
            );

            final end =
                _asDouble(
              window['end'],
            );

            final duration =
                (end - start)
                    .clamp(
              0.1,
              double.infinity,
            );

            // 10초 구간 기준 약 100px.
            // 마지막 짧은 구간은 상대적으로 짧게 표시.
            final width =
                (duration * 10)
                    .clamp(
              60.0,
              120.0,
            );

            final level =
                window['level']
                        ?.toString() ??
                    'low';

            final selected =
                index ==
                    selectedIndex;

            return GestureDetector(
              onTap: () {
                onSelected(
                  index,
                );
              },
              child:
                  Padding(
                padding:
                    const EdgeInsets.only(
                  right:
                      4,
                ),
                child:
                    Column(
                  crossAxisAlignment:
                      CrossAxisAlignment.start,
                  children: [
                    AnimatedContainer(
                      duration:
                          const Duration(
                        milliseconds:
                            180,
                      ),
                      width:
                          width,
                      height:
                          selected
                              ? 54
                              : 46,
                      decoration:
                          BoxDecoration(
                        color:
                            _riskColor(
                          level,
                        ),
                        borderRadius:
                            BorderRadius.circular(
                          10,
                        ),
                        border:
                            selected
                                ? Border.all(
                                    color:
                                        Colors.black87,
                                    width:
                                        3,
                                  )
                                : null,
                      ),
                      child:
                          Center(
                        child:
                            Text(
                          _riskLabel(
                            level,
                          ),
                          style:
                              TextStyle(
                            fontSize:
                                12,
                            fontWeight:
                                FontWeight.bold,
                            color:
                                _riskTextColor(
                              level,
                            ),
                          ),
                        ),
                      ),
                    ),

                    const SizedBox(
                      height: 7,
                    ),

                    SizedBox(
                      width: width,
                      child: Row(
                        mainAxisAlignment:
                            MainAxisAlignment.spaceBetween,
                        children: [
                          Text(
                            _formatTime(
                              start,
                            ),
                            style: const TextStyle(
                              fontSize: 11,
                              color: Colors.black54,
                            ),
                          ),

                          if (
                              index ==
                              heatmap.length - 1
                          )
                            Text(
                              _formatTime(
                                end,
                              ),
                              style: const TextStyle(
                                fontSize: 11,
                                color: Colors.black54,
                              ),
                            ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            );
          },
        ),
      ),
    );
  }
}


// ============================================================
// WINDOW DETAIL
// ============================================================

class _WindowDetailCard
    extends StatelessWidget {
  final Map<String, dynamic> window;


  const _WindowDetailCard({
    required this.window,
  });


  @override
  Widget build(
    BuildContext context,
  ) {
    final start =
        _asDouble(
      window['start'],
    );

    final end =
        _asDouble(
      window['end'],
    );

    final score =
        window['score'] ?? 0;

    final level =
        window['level']
                ?.toString() ??
            'low';

    final reasons =
        List<String>.from(
      window['reasons'] ?? [],
    );

    return _SectionCard(
      title:
          '${_formatTime(start)} ~ ${_formatTime(end)} 상세',
      child:
          Column(
        children: [
          Row(
            children: [
              Expanded(
                child:
                    _DetailItem(
                  label:
                      '위험도',
                  value:
                      '${_riskLabel(level)} · $score점',
                ),
              ),

              const SizedBox(
                width:
                    12,
              ),

              Expanded(
                child:
                    _DetailItem(
                  label:
                      '발표 속도',
                  value:
                      _paceText(
                    window[
                            'pace_level']
                        ?.toString(),
                  ),
                ),
              ),
            ],
          ),

          const SizedBox(
            height: 12,
          ),

          Row(
            children: [
              Expanded(
                child:
                    _DetailItem(
                  label:
                      '음성 톤',
                  value:
                      _emotionText(
                    window[
                            'emotion_signal']
                        ?.toString(),
                  ),
                ),
              ),

              const SizedBox(
                width:
                    12,
              ),

              Expanded(
                child:
                    _DetailItem(
                  label:
                      '멈춤',
                  value:
                      '${window['pause_count'] ?? 0}회',
                ),
              ),
            ],
          ),

          const SizedBox(
            height: 12,
          ),

          Row(
            children: [
              Expanded(
                child:
                    _DetailItem(
                  label:
                      '추임새',
                  value:
                      '${window['filler_count'] ?? 0}회',
                ),
              ),

              const SizedBox(
                width:
                    12,
              ),

              Expanded(
                child:
                    _DetailItem(
                  label:
                      '반복',
                  value:
                      '${window['repetition_count'] ?? 0}회',
                ),
              ),
            ],
          ),

          const SizedBox(
            height:
                18,
          ),

          const Divider(),

          const SizedBox(
            height:
                10,
          ),

          Align(
            alignment:
                Alignment.centerLeft,
            child:
                Text(
              '이 구간에서 확인된 신호',
              style:
                  TextStyle(
                fontSize:
                    13,
                fontWeight:
                    FontWeight.w600,
                color:
                    Colors.grey.shade700,
              ),
            ),
          ),

          const SizedBox(
            height:
                10,
          ),

          if (
              reasons.isEmpty
          )
            const Align(
              alignment:
                  Alignment.centerLeft,
              child:
                  Text(
                '특별한 개선 신호가 탐지되지 않았습니다.',
                style:
                    TextStyle(
                  fontSize:
                      13,
                  color:
                      Colors.black54,
                ),
              ),
            )
          else
            ...reasons.map(
              (
                reason,
              ) {
                return Padding(
                  padding:
                      const EdgeInsets.only(
                    bottom:
                        7,
                  ),
                  child:
                      Row(
                    crossAxisAlignment:
                        CrossAxisAlignment.start,
                    children: [
                      const Text(
                        '• ',
                        style:
                            TextStyle(
                          fontSize:
                              13,
                        ),
                      ),

                      Expanded(
                        child:
                            Text(
                          _replaceBackendTerms(
                            reason,
                          ),
                          style:
                              const TextStyle(
                            fontSize:
                                13,
                            height:
                                1.4,
                          ),
                        ),
                      ),
                    ],
                  ),
                );
              },
            ),
        ],
      ),
    );
  }
}


// ============================================================
// COMPONENTS
// ============================================================

class _MetricCard extends StatelessWidget {
  final String title;
  final String value;
  final String subtitle;


  const _MetricCard({
    required this.title,
    required this.value,
    this.subtitle = '',
  });


  @override
  Widget build(
    BuildContext context,
  ) {
    return Container(
      padding:
          const EdgeInsets.all(
        16,
      ),
      decoration:
          BoxDecoration(
        color:
            Colors.grey.shade50,
        borderRadius:
            BorderRadius.circular(
          18,
        ),
        border:
            Border.all(
          color:
              Colors.grey.shade200,
        ),
      ),
      child:
          Column(
        crossAxisAlignment:
            CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style:
                const TextStyle(
              fontSize:
                  13,
              color:
                  Colors.black54,
            ),
          ),

          const SizedBox(
            height:
                8,
          ),

          Text(
            value,
            style:
                const TextStyle(
              fontSize:
                  25,
              fontWeight:
                  FontWeight.bold,
            ),
          ),

          if (
              subtitle.isNotEmpty
          ) ...[
            const SizedBox(
              height:
                  4,
            ),

            Text(
              subtitle,
              style:
                  const TextStyle(
                fontSize:
                    12,
                color:
                    Colors.black45,
              ),
            ),
          ],
        ],
      ),
    );
  }
}


class _DetailItem extends StatelessWidget {
  final String label;
  final String value;


  const _DetailItem({
    required this.label,
    required this.value,
  });


  @override
  Widget build(
    BuildContext context,
  ) {
    return Container(
      width:
          double.infinity,
      padding:
          const EdgeInsets.all(
        12,
      ),
      decoration:
          BoxDecoration(
        color:
            Colors.grey.shade50,
        borderRadius:
            BorderRadius.circular(
          12,
        ),
      ),
      child:
          Column(
        crossAxisAlignment:
            CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style:
                const TextStyle(
              fontSize:
                  11,
              color:
                  Colors.black45,
            ),
          ),

          const SizedBox(
            height:
                5,
          ),

          Text(
            value,
            style:
                const TextStyle(
              fontSize:
                  14,
              fontWeight:
                  FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}


class _SectionCard extends StatelessWidget {
  final String title;
  final Widget child;
  final Widget? trailing;

  const _SectionCard({
    required this.title,
    required this.child,
    this.trailing,
  });


  @override
  Widget build(
    BuildContext context,
  ) {
    return Container(
      width:
          double.infinity,
      padding:
          const EdgeInsets.all(
        18,
      ),
      decoration:
          BoxDecoration(
        color:
            Colors.white,
        borderRadius:
            BorderRadius.circular(
          18,
        ),
        border:
            Border.all(
          color:
              Colors.grey.shade200,
        ),
        boxShadow: [
          BoxShadow(
            blurRadius:
                10,
            offset:
                const Offset(
              0,
              2,
            ),
            color:
                Colors.black.withValues(
              alpha:
                  0.04,
            ),
          ),
        ],
      ),
      child:
          Column(
        crossAxisAlignment:
            CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  title,
                  style: const TextStyle(
                    fontSize: 17,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),

              if (trailing != null)
                trailing!,
            ],
          ),

          const SizedBox(
            height: 12,
          ),

          child,
        ],
      ),
    );
  }
}

class _OverallStatusBadge
    extends StatelessWidget {
  final String level;

  const _OverallStatusBadge({
    required this.level,
  });

  @override
  Widget build(
    BuildContext context,
  ) {
    final backgroundColor =
        _overallStatusColor(
      level,
    );

    final textColor =
        _overallStatusTextColor(
      level,
    );

    return Container(
      padding:
          const EdgeInsets.symmetric(
        horizontal: 12,
        vertical: 7,
      ),
      decoration:
          BoxDecoration(
        color: backgroundColor,
        borderRadius:
            BorderRadius.circular(
          999,
        ),
      ),
      child: Text(
        _overallStatusText(
          level,
        ),
        style: TextStyle(
          fontSize: 13,
          fontWeight:
              FontWeight.bold,
          color: textColor,
        ),
      ),
    );
  }
}

// ============================================================
// TEXT MAPPING
// ============================================================

String _paceText(
  String? level,
) {
  switch (level) {
    case 'slow':
      return '느림';

    case 'slightly_slow':
      return '약간 느림';

    case 'normal':
      return '적절';

    case 'slightly_fast':
      return '약간 빠름';

    case 'fast':
      return '빠름';

    default:
      return '판정 없음';
  }
}


String _emotionText(
  String? emotion,
) {
  switch (
      emotion?.toLowerCase()
  ) {
    case 'neutral':
      return '차분한 톤';

    case 'happy':
      return '밝은 톤';

    case 'sad':
      return '가라앉은 톤';

    case 'angry':
      return '강한 톤';

    case 'fearful':
      return '불안정한 톤';

    case 'surprised':
      return '변화가 큰 톤';

    case 'disgusted':
      return '거친 톤';

    case 'emo_unknown':
    case 'unknown':
      return '톤 신호 부족';

    default:
      return '분석 불가';
  }
}


String _riskLabel(
  String level,
) {
  switch (level) {
    case 'high':
      return '주의';

    case 'medium':
      return '보통';

    case 'low':
      return '안정';

    default:
      return '분석 없음';
  }
}


Color _riskColor(
  String level,
) {
  switch (level) {
    case 'high':
      return const Color(
        0xFFFF7B7B,
      );

    case 'medium':
      return const Color(
        0xFFFFD166,
      );

    case 'low':
      return const Color(
        0xFF72D69A,
      );

    default:
      return Colors.grey.shade300;
  }
}


Color _riskTextColor(
  String level,
) {
  switch (level) {
    case 'high':
      return const Color(
        0xFF5D1010,
      );

    case 'medium':
      return const Color(
        0xFF5A4300,
      );

    case 'low':
      return const Color(
        0xFF12492A,
      );

    default:
      return Colors.black54;
  }
}


String _replaceBackendTerms(
  String text,
) {
  return text
      .replaceAll(
        'pause',
        '멈춤',
      )
      .replaceAll(
        'Pause',
        '멈춤',
      );
}

String _overallStatusText(
  String level,
) {
  switch (level) {
    case 'low':
      return '좋음';

    case 'medium':
      return '주의';

    case 'high':
      return '안 좋음';

    default:
      return '분석 없음';
  }
}


Color _overallStatusColor(
  String level,
) {
  switch (level) {
    case 'low':
      return const Color(
        0xFFDDF7E8,
      );

    case 'medium':
      return const Color(
        0xFFFFF0C2,
      );

    case 'high':
      return const Color(
        0xFFFFDADA,
      );

    default:
      return Colors.grey.shade200;
  }
}


Color _overallStatusTextColor(
  String level,
) {
  switch (level) {
    case 'low':
      return const Color(
        0xFF187A45,
      );

    case 'medium':
      return const Color(
        0xFF8A6500,
      );

    case 'high':
      return const Color(
        0xFFA32929,
      );

    default:
      return Colors.black54;
  }
}


// ============================================================
// UTILS
// ============================================================

String _pausePercent(
  dynamic ratio,
) {
  final value =
      ratio is num
          ? ratio.toDouble()
          : 0.0;

  return (
    value * 100
  ).toStringAsFixed(
    1,
  );
}


double _asDouble(
  dynamic value,
) {
  if (
      value is num
  ) {
    return value.toDouble();
  }

  return 0.0;
}


String _formatTime(
  double seconds,
) {
  final totalSeconds =
      seconds.round();

  final minutes =
      totalSeconds ~/ 60;

  final remainingSeconds =
      totalSeconds % 60;

  if (
      minutes > 0
  ) {
    return '$minutes:${remainingSeconds.toString().padLeft(2, '0')}';
  }

  return '${totalSeconds}초';
}