import 'package:flutter/material.dart';

import '../models/app_models.dart';
import '../theme/app_colors.dart';

class HomeLoading extends StatelessWidget {
  const HomeLoading({super.key, required this.mode});

  final RecordMode mode;

  @override
  Widget build(BuildContext context) {
    final isMotion = mode == RecordMode.voiceMotion;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Padding(
          padding: EdgeInsets.only(left: 20, right: 20, top: 12, bottom: 8),
          child: Text(
            'Speechinx',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: AppColors.gray900,
            ),
          ),
        ),
        Expanded(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const SizedBox(
                  width: 96,
                  height: 96,
                  child: CircularProgressIndicator(
                    strokeWidth: 8,
                    strokeCap: StrokeCap.round,
                    color: AppColors.violet600,
                    backgroundColor: AppColors.violet100,
                  ),
                ),
                const SizedBox(height: 24),
                Text(
                  isMotion ? '발표 음성과 동작을 분석하고 있어요...' : '발표를 분석하고 있어요...',
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                    color: AppColors.gray900,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  isMotion
                      ? '음성 분석과 관련 분석을 함께 처리하고 있어요'
                      : '발표 속도, 발음, 습관어를 추출하고 있습니다.',
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    fontSize: 14,
                    color: AppColors.gray500,
                  ),
                ),
                const SizedBox(height: 24),
                const Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text('녹음 정지',
                        style: TextStyle(fontSize: 12, color: AppColors.gray400)),
                    SizedBox(width: 8),
                    Icon(Icons.arrow_forward, size: 14, color: AppColors.gray300),
                    SizedBox(width: 8),
                    Text('분석 완료',
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w500,
                          color: AppColors.violet600,
                        )),
                  ],
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}
