import 'package:flutter/material.dart';

import '../models/app_models.dart';
import '../theme/app_colors.dart';
import '../widgets/common.dart';

class AnalysisSummary extends StatelessWidget {
  const AnalysisSummary({
    super.key,
    required this.summary,
    required this.level,
    required this.metrics,
    required this.onBack,
    required this.onDetail,
  });

  final String summary;
  final SegmentLevel level;
  final List<MetricData> metrics;
  final VoidCallback onBack;
  final VoidCallback onDetail;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.only(left: 20, right: 20, top: 12, bottom: 8),
          child: Row(
            children: [
              GestureDetector(
                onTap: onBack,
                child: const Icon(Icons.chevron_left, size: 24, color: AppColors.gray700),
              ),
              const SizedBox(width: 8),
              const Text(
                '발표 분석 결과',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  color: AppColors.gray900,
                ),
              ),
            ],
          ),
        ),
        Expanded(
          child: SingleChildScrollView(
            padding: const EdgeInsets.only(left: 20, right: 20, bottom: 16),
            child: Column(
              children: [
                OverallCard(summary: summary, level: level),
                const SizedBox(height: 16),
                MetricsCard(metrics: metrics),
              ],
            ),
          ),
        ),
        Padding(
          padding: const EdgeInsets.only(left: 20, right: 20, bottom: 20),
          child: GestureDetector(
            onTap: onDetail,
            child: Container(
              height: 56,
              decoration: BoxDecoration(
                color: AppColors.violet600,
                borderRadius: BorderRadius.circular(16),
              ),
              child: const Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    '상세 보기',
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                      color: AppColors.white,
                    ),
                  ),
                  SizedBox(width: 8),
                  Icon(Icons.expand_more, size: 20, color: AppColors.white),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }
}
