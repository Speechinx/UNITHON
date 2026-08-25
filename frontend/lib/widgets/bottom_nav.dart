import 'package:flutter/material.dart';

import '../models/app_models.dart';
import '../theme/app_colors.dart';

class BottomNav extends StatelessWidget {
  const BottomNav({super.key, required this.tab, required this.onTab});

  final AppTab tab;
  final ValueChanged<AppTab> onTab;

  static const _items = <(AppTab, String, IconData)>[
    (AppTab.home, '홈', Icons.mic_none),
    (AppTab.history, '기록', Icons.menu),
    (AppTab.mypage, '마이페이지', Icons.person_outline),
  ];

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        color: AppColors.white,
        border: Border(top: BorderSide(color: AppColors.gray100)),
      ),
      child: Row(
        children: [
          for (final (id, label, icon) in _items)
            Expanded(
              child: InkWell(
                onTap: () => onTab(id),
                child: Padding(
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  child: Column(
                    children: [
                      Icon(
                        icon,
                        size: 22,
                        color: tab == id ? AppColors.violet600 : AppColors.gray400,
                      ),
                      const SizedBox(height: 4),
                      Text(
                        label,
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w500,
                          color: tab == id ? AppColors.violet600 : AppColors.gray400,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
