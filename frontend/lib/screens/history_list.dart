import 'package:flutter/material.dart';

import '../models/app_models.dart';
import '../theme/app_colors.dart';
import '../widgets/common.dart';

class HistoryList extends StatelessWidget {
  const HistoryList({
    super.key,
    required this.items,
    required this.onDelete,
    required this.onTap,
  });

  final List<HistoryItem> items;
  final ValueChanged<int> onDelete;
  final ValueChanged<int> onTap;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Padding(
          padding: EdgeInsets.only(left: 20, right: 20, top: 12, bottom: 8),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                '발표 기록',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  color: AppColors.gray900,
                ),
              ),
              Icon(Icons.filter_alt_outlined,
                  size: 20, color: AppColors.gray700),
            ],
          ),
        ),
        Expanded(
          child: ListView.separated(
            padding: const EdgeInsets.only(left: 20, right: 20, bottom: 16),
            itemCount: items.length,
            separatorBuilder: (_, _) => const SizedBox(height: 12),
            itemBuilder: (context, i) {
              final item = items[i];
              final isCaution = item.badge == '주의';
              return GestureDetector(
                onTap: () => onTap(i),
                child: AppCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Text(
                                item.date,
                                style: const TextStyle(
                                  fontSize: 12,
                                  color: AppColors.gray400,
                                ),
                              ),
                              const SizedBox(width: 8),
                              StatusBadge(
                                label: item.badge,
                                background: isCaution
                                    ? AppColors.amber100
                                    : AppColors.red100,
                                foreground: isCaution
                                    ? AppColors.amber700
                                    : AppColors.red700,
                              ),
                            ],
                          ),
                          GestureDetector(
                            onTap: () => onDelete(i),
                            child: const Icon(Icons.delete_outline,
                                size: 18, color: AppColors.gray400),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Text(
                        item.title,
                        style: const TextStyle(
                          fontSize: 15,
                          fontWeight: FontWeight.bold,
                          color: AppColors.gray900,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        item.detail,
                        style: const TextStyle(
                          fontSize: 12,
                          color: AppColors.gray500,
                        ),
                      ),
                    ],
                  ),
                ),
              );
            },
          ),
        ),
      ],
    );
  }
}

class HistoryEmpty extends StatelessWidget {
  const HistoryEmpty({super.key, required this.onStart});

  final VoidCallback onStart;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Padding(
          padding: EdgeInsets.only(left: 20, right: 20, top: 12, bottom: 8),
          child: Text(
            '발표 기록',
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
                const Icon(Icons.help_outline,
                    size: 48, color: AppColors.gray300),
                const SizedBox(height: 16),
                const Text(
                  '아직 분석한 발표가 없어요',
                  style: TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.bold,
                    color: AppColors.gray900,
                  ),
                ),
                const SizedBox(height: 4),
                const Text(
                  '첫 번째 발표를 녹음하고 AI 분석을 경험해보세요',
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 14, color: AppColors.gray500),
                ),
                const SizedBox(height: 16),
                GestureDetector(
                  onTap: onStart,
                  child: Container(
                    width: double.infinity,
                    height: 52,
                    decoration: BoxDecoration(
                      color: AppColors.violet600,
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: const Center(
                      child: Text(
                        '발표 연습하러 가기',
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.bold,
                          color: AppColors.white,
                        ),
                      ),
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
}
