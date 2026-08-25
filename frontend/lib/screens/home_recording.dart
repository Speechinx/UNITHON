import 'package:camera/camera.dart';
import 'package:flutter/material.dart';

import '../models/app_models.dart';
import '../posture/reaction_avatar.dart';
import '../theme/app_colors.dart';

class HomeRecording extends StatelessWidget {
  const HomeRecording({
    super.key,
    required this.mode,
    required this.seconds,
    required this.onStop,
    required this.cameraController,
    required this.avatarState,
  });

  final RecordMode mode;
  final int seconds;
  final VoidCallback onStop;
  final CameraController? cameraController;
  final String avatarState;

  @override
  Widget build(BuildContext context) {
    final mm = (seconds ~/ 60).toString().padLeft(2, '0');
    final ss = (seconds % 60).toString().padLeft(2, '0');

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.only(left: 20, right: 20, top: 12, bottom: 8),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'AI Presentation Coach',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  color: AppColors.gray900,
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
                decoration: BoxDecoration(
                  color: AppColors.red50,
                  border: Border.all(color: AppColors.red200),
                  borderRadius: BorderRadius.circular(999),
                ),
                child: const Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    _BlinkingDot(),
                    SizedBox(width: 6),
                    Text(
                      'REC',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                        color: AppColors.red600,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
        Expanded(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            child: Column(
              children: [
                if (mode == RecordMode.voiceMotion)
                  Expanded(child: _cameraSection())
                else
                  Expanded(child: _voiceSection()),

                // Timer
                Column(
                  children: [
                    Text(
                      '$mm:$ss',
                      style: const TextStyle(
                        fontSize: 46,
                        fontWeight: FontWeight.bold,
                        color: AppColors.gray900,
                        fontFeatures: [FontFeature.tabularFigures()],
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      mode == RecordMode.voiceMotion
                          ? '카메라 없이 음성만 계속 진행'
                          : '목소리가 정상적으로 입력되고 있습니다',
                      style: const TextStyle(
                        fontSize: 14,
                        color: AppColors.gray500,
                      ),
                    ),
                  ],
                ),

                const SizedBox(height: 24),
                Row(
                  children: [
                    const Expanded(child: Divider(color: AppColors.gray200, height: 1)),
                    const Padding(
                      padding: EdgeInsets.symmetric(horizontal: 8),
                      child: Text('녹음 시작',
                          style: TextStyle(fontSize: 12, color: AppColors.gray400)),
                    ),
                    const Expanded(child: Divider(color: AppColors.gray200, height: 1)),
                    const Padding(
                      padding: EdgeInsets.symmetric(horizontal: 8),
                      child: Text('녹음 정지',
                          style: TextStyle(fontSize: 12, color: AppColors.gray400)),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                GestureDetector(
                  onTap: onStop,
                  child: Container(
                    height: 56,
                    margin: const EdgeInsets.only(bottom: 24),
                    decoration: BoxDecoration(
                      color: AppColors.gray900,
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: const Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.stop, size: 22, color: AppColors.white),
                        SizedBox(width: 12),
                        Text(
                          '정지',
                          style: TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                            color: AppColors.white,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _voiceSection() {
    return Column(
      children: [
        const SizedBox(height: 16),
        const Align(
          alignment: Alignment.centerLeft,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                '발표 진행 중...',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w500,
                  color: AppColors.red500,
                ),
              ),
              SizedBox(height: 4),
              Text(
                '자연스럽고 편안하게\n준비한 발표를 말해보세요',
                style: TextStyle(
                  fontSize: 20,
                  height: 1.35,
                  fontWeight: FontWeight.bold,
                  color: AppColors.gray900,
                ),
              ),
            ],
          ),
        ),
        Expanded(
          child: Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Container(
                  width: 128,
                  height: 128,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: AppColors.violet50,
                    border: Border.all(color: AppColors.violet100, width: 4),
                  ),
                  child: const Icon(Icons.mic, size: 52, color: AppColors.violet600),
                ),
                const SizedBox(height: 12),
                const Text('홈으로 이동',
                    style: TextStyle(fontSize: 12, color: AppColors.gray400)),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _cameraSection() {
    final controller = cameraController;
    final isReady = controller != null && controller.value.isInitialized;

    return Column(
      children: [
        const SizedBox(height: 8),
        const Align(
          alignment: Alignment.centerLeft,
          child: Text(
            '자세를 실시간으로 분석하고 있어요',
            style: TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w500,
              color: AppColors.red500,
            ),
          ),
        ),
        const SizedBox(height: 12),
        Expanded(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxHeight: 288),
            child: Container(
              width: double.infinity,
              clipBehavior: Clip.antiAlias,
              decoration: BoxDecoration(
                color: AppColors.gray900,
                borderRadius: BorderRadius.circular(16),
              ),
              child: Stack(
                fit: StackFit.expand,
                children: [
                  if (isReady)
                    Center(
                      child: AspectRatio(
                        aspectRatio: controller.value.aspectRatio,
                        child: CameraPreview(controller),
                      ),
                    )
                  else
                    const Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.videocam_outlined,
                              size: 32, color: AppColors.gray400),
                          SizedBox(height: 8),
                          Text('카메라를 준비하고 있어요',
                              style: TextStyle(
                                  fontSize: 14, color: AppColors.gray500)),
                        ],
                      ),
                    ),
                  Positioned(
                    top: 12,
                    right: 12,
                    child: ReactionAvatar(state: avatarState, size: 56),
                  ),
                ],
              ),
            ),
          ),
        ),
        const SizedBox(height: 16),
        const _Waveform(),
      ],
    );
  }
}

class _Dot extends StatelessWidget {
  const _Dot({required this.color, required this.size});

  final Color color;
  final double size;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(color: color, shape: BoxShape.circle),
    );
  }
}

/// animate-pulse 대체
class _BlinkingDot extends StatefulWidget {
  const _BlinkingDot();

  @override
  State<_BlinkingDot> createState() => _BlinkingDotState();
}

class _BlinkingDotState extends State<_BlinkingDot>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 900),
  )..repeat(reverse: true);

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: Tween<double>(begin: 0.35, end: 1).animate(_controller),
      child: const _Dot(color: AppColors.red500, size: 8),
    );
  }
}

/// wave-bar 애니메이션 대체
class _Waveform extends StatefulWidget {
  const _Waveform();

  @override
  State<_Waveform> createState() => _WaveformState();
}

class _WaveformState extends State<_Waveform>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1000),
  )..repeat();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, _) {
        return Row(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            for (var i = 0; i < 20; i++)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 4),
                child: Container(
                  width: 4,
                  height: _barHeight(i),
                  decoration: BoxDecoration(
                    color: AppColors.violet600,
                    borderRadius: BorderRadius.circular(999),
                  ),
                ),
              ),
          ],
        );
      },
    );
  }

  double _barHeight(int index) {
    final t = (_controller.value + index * 0.05) % 1.0;
    final wave = 1 - (2 * t - 1).abs();
    return 4 + wave * 26;
  }
}
