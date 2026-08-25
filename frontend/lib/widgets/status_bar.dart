import 'package:flutter/material.dart';

import '../theme/app_colors.dart';

/// 목업 상태 바 (9:41 · 신호 · 와이파이 · 배터리)
class FakeStatusBar extends StatelessWidget {
  const FakeStatusBar({super.key});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(left: 16, right: 16, top: 12, bottom: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          const Text(
            '9:41',
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w600,
              color: AppColors.gray800,
            ),
          ),
          Row(
            children: [
              const _SignalBars(),
              const SizedBox(width: 4),
              const Icon(Icons.wifi, size: 14, color: AppColors.gray800),
              const SizedBox(width: 4),
              _battery(),
            ],
          ),
        ],
      ),
    );
  }

  Widget _battery() {
    return Row(
      children: [
        Container(
          width: 24,
          height: 12,
          padding: const EdgeInsets.all(1.5),
          decoration: BoxDecoration(
            border: Border.all(color: AppColors.gray700),
            borderRadius: BorderRadius.circular(3),
          ),
          child: Container(
            decoration: BoxDecoration(
              color: AppColors.gray800,
              borderRadius: BorderRadius.circular(1.5),
            ),
          ),
        ),
        const SizedBox(width: 1),
        Container(
          width: 2,
          height: 5,
          decoration: const BoxDecoration(
            color: AppColors.gray700,
            borderRadius: BorderRadius.horizontal(right: Radius.circular(2)),
          ),
        ),
      ],
    );
  }
}

class _SignalBars extends StatelessWidget {
  const _SignalBars();

  @override
  Widget build(BuildContext context) {
    const heights = [5.0, 7.0, 9.0, 11.0];
    return Row(
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [
        for (final h in heights)
          Container(
            width: 3,
            height: h,
            margin: const EdgeInsets.only(left: 1.5),
            decoration: BoxDecoration(
              color: AppColors.gray800,
              borderRadius: BorderRadius.circular(1),
            ),
          ),
      ],
    );
  }
}
