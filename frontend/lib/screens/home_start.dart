import 'package:flutter/material.dart';

import '../models/app_models.dart';
import '../theme/app_colors.dart';

class HomeStart extends StatelessWidget {
  const HomeStart({
    super.key,
    required this.mode,
    required this.onModeChanged,
    required this.onRecord,
    required this.onUpload,
    this.errorMessage,
  });

  final RecordMode mode;
  final ValueChanged<RecordMode> onModeChanged;
  final VoidCallback onRecord;
  final VoidCallback onUpload;
  final String? errorMessage;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Header
        Padding(
          padding: const EdgeInsets.only(left: 20, right: 20, top: 12, bottom: 8),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Expanded(
                child: Text(
                  'AI Presentation Coach',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                    color: AppColors.gray900,
                  ),
                ),
              ),
              Container(
                width: 36,
                height: 36,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  border: Border.all(color: AppColors.gray200),
                ),
                child: const Icon(
                  Icons.help_outline,
                  size: 18,
                  color: AppColors.gray500,
                ),
              ),
            ],
          ),
        ),

        // Headline + mode toggle
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'AI SPEAKER COACH',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  letterSpacing: 1.2,
                  color: AppColors.violet600,
                ),
              ),
              const SizedBox(height: 4),
              const Text(
                '발표를 녹음하고\nAI 피드백을 받아보세요',
                style: TextStyle(
                  fontSize: 24,
                  height: 1.25,
                  fontWeight: FontWeight.bold,
                  color: AppColors.gray900,
                ),
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  _ModeChip(
                    label: '음성만',
                    selected: mode == RecordMode.voice,
                    onTap: () => onModeChanged(RecordMode.voice),
                  ),
                  const SizedBox(width: 8),
                  _ModeChip(
                    label: '음성+모션(카메라)',
                    selected: mode == RecordMode.voiceMotion,
                    onTap: () => onModeChanged(RecordMode.voiceMotion),
                  ),
                ],
              ),
              if (errorMessage != null) ...[
                const SizedBox(height: 12),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AppColors.red50,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    errorMessage!,
                    style: const TextStyle(
                      fontSize: 12,
                      color: AppColors.red600,
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),

        // Mic button, centered
        Expanded(
          child: Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                _PulsingMicButton(onTap: onRecord),
                const SizedBox(height: 24),
                const Text(
                  '발표 준비가 되셨나요?',
                  style: TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w600,
                    color: AppColors.gray800,
                  ),
                ),
                const SizedBox(height: 4),
                const Text(
                  '마이크 버튼을 눌러 녹음을 시작하거나 WAV 파일을 업로드\n해 발표 습관을 분석해보세요',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 12,
                    height: 1.6,
                    color: AppColors.gray500,
                  ),
                ),
              ],
            ),
          ),
        ),

        // Upload
        Padding(
          padding: const EdgeInsets.only(left: 20, right: 20, bottom: 10),
          child: GestureDetector(
            onTap: onUpload,
            child: CustomPaint(
              painter: _DashedBorderPainter(),
              child: const SizedBox(
                height: 48,
                child: Center(
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.file_upload_outlined,
                          size: 18, color: AppColors.gray600),
                      SizedBox(width: 8),
                      Text(
                        '파일 업로드',
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w500,
                          color: AppColors.gray600,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _ModeChip extends StatelessWidget {
  const _ModeChip({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 9),
        decoration: BoxDecoration(
          color: selected ? AppColors.violet600 : AppColors.gray100,
          borderRadius: BorderRadius.circular(999),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w600,
            color: selected ? AppColors.white : AppColors.gray500,
          ),
        ),
      ),
    );
  }
}

/// 링이 퍼지는 마이크 버튼 (pulse-ring 애니메이션 대체)
class _PulsingMicButton extends StatefulWidget {
  const _PulsingMicButton({required this.onTap});

  final VoidCallback onTap;

  @override
  State<_PulsingMicButton> createState() => _PulsingMicButtonState();
}

class _PulsingMicButtonState extends State<_PulsingMicButton>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 2000),
  )..repeat();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 180,
      height: 180,
      child: Stack(
        alignment: Alignment.center,
        children: [
          AnimatedBuilder(
            animation: _controller,
            builder: (context, _) {
              final t = _controller.value;
              return Stack(
                alignment: Alignment.center,
                children: [
                  for (final delay in [0.0, 0.5])
                    _ring((t + delay) % 1.0),
                ],
              );
            },
          ),
          GestureDetector(
            onTap: widget.onTap,
            child: Container(
              width: 112,
              height: 112,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: AppColors.violet100,
                border: Border.all(color: AppColors.violet300, width: 2),
              ),
              child: const Icon(Icons.mic, size: 48, color: AppColors.violet600),
            ),
          ),
        ],
      ),
    );
  }

  Widget _ring(double t) {
    return Container(
      width: 112 + 68 * t,
      height: 112 + 68 * t,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: AppColors.violet100.withValues(alpha: 0.5 * (1 - t)),
      ),
    );
  }
}

/// border-2 border-dashed 대체
class _DashedBorderPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = AppColors.gray300
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2;

    final rrect = RRect.fromRectAndRadius(
      Offset.zero & size,
      const Radius.circular(12),
    );
    final path = Path()..addRRect(rrect);

    const dash = 6.0;
    const gap = 5.0;
    for (final metric in path.computeMetrics()) {
      var distance = 0.0;
      while (distance < metric.length) {
        canvas.drawPath(
          metric.extractPath(distance, distance + dash),
          paint,
        );
        distance += dash + gap;
      }
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
