import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../models/app_models.dart';
import '../theme/app_colors.dart';
import '../widgets/common.dart';

class AnalysisDetail extends StatefulWidget {
  const AnalysisDetail({
    super.key,
    required this.summary,
    required this.level,
    required this.metrics,
    required this.segments,
    required this.strengths,
    required this.oneLineCoaching,
    required this.improvements,
    required this.practiceGoals,
    required this.fullScript,
    required this.onBack,
  });

  final String summary;
  final SegmentLevel level;
  final List<MetricData> metrics;
  final List<Segment> segments;
  final List<String> strengths;
  final String oneLineCoaching;
  final List<Map<String, dynamic>> improvements;
  final List<String> practiceGoals;
  final String fullScript;
  final VoidCallback onBack;

  @override
  State<AnalysisDetail> createState() => _AnalysisDetailState();
}

class _AnalysisDetailState extends State<AnalysisDetail> {
  DetailTab _tab = DetailTab.flow;
  bool _expanded = true;
  bool _copied = false;
  int _selectedSeg = 0;

  final ScrollController _timelineScrollController = ScrollController();

  static const _tabLabels = {
    DetailTab.flow: '발표 흐름',
    DetailTab.improve: '개선사항',
    DetailTab.script: '발표 스크립트',
  };

  @override
  void dispose() {
    _timelineScrollController.dispose();
    super.dispose();
  }

  Future<void> _copyScript() async {
    await Clipboard.setData(ClipboardData(text: widget.fullScript));
    if (!mounted) return;
    setState(() => _copied = true);
    await Future<void>.delayed(const Duration(seconds: 2));
    if (!mounted) return;
    setState(() => _copied = false);
  }

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
                onTap: widget.onBack,
                child: const Icon(Icons.chevron_left,
                    size: 24, color: AppColors.gray700),
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
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                OverallCard(summary: widget.summary, level: widget.level),
                const SizedBox(height: 16),
                MetricsCard(
                  metrics: widget.metrics,
                  footer: GestureDetector(
                    onTap: () => setState(() => _expanded = !_expanded),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          '상세 분석 ${_expanded ? "닫기" : "열기"}',
                          style: const TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.w500,
                            color: AppColors.violet600,
                          ),
                        ),
                        const SizedBox(width: 4),
                        Icon(
                          _expanded ? Icons.expand_less : Icons.expand_more,
                          size: 16,
                          color: AppColors.violet600,
                        ),
                      ],
                    ),
                  ),
                ),
                if (_expanded) ...[
                  const SizedBox(height: 16),
                  _tabBar(),
                  const SizedBox(height: 16),
                  switch (_tab) {
                    DetailTab.flow => _flowTab(),
                    DetailTab.improve => _improveTab(),
                    DetailTab.script => _scriptTab(),
                  },
                ],
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _tabBar() {
    return Row(
      children: [
        for (final t in DetailTab.values)
          Padding(
            padding: const EdgeInsets.only(right: 8),
            child: GestureDetector(
              onTap: () => setState(() => _tab = t),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 180),
                padding:
                    const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
                decoration: BoxDecoration(
                  color: _tab == t ? AppColors.violet600 : AppColors.gray100,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  _tabLabels[t]!,
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                    color: _tab == t ? AppColors.white : AppColors.gray500,
                  ),
                ),
              ),
            ),
          ),
      ],
    );
  }

  Widget _flowTab() {
    final segments = widget.segments;

    if (segments.isEmpty) {
      return const AppCard(
        child: Text(
          '구간 분석 결과가 없습니다.',
          style: TextStyle(fontSize: 13, color: AppColors.gray500),
        ),
      );
    }

    final selectedIndex = _selectedSeg.clamp(0, segments.length - 1);
    final seg = segments[selectedIndex];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Timeline
        AppCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text(
                '발표 흐름',
                style: TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.bold,
                  color: AppColors.gray900,
                ),
              ),
              const SizedBox(height: 12),
              ScrollbarTheme(
                data: ScrollbarThemeData(
                  thumbColor: WidgetStateProperty.all(Colors.black26),
                  trackColor: WidgetStateProperty.all(Colors.black12),
                  trackBorderColor:
                      WidgetStateProperty.all(Colors.transparent),
                  thickness: WidgetStateProperty.all(5),
                  radius: const Radius.circular(999),
                  crossAxisMargin: 0,
                ),
                child: Scrollbar(
                  controller: _timelineScrollController,
                  thumbVisibility: true,
                  trackVisibility: true,
                  child: SingleChildScrollView(
                    controller: _timelineScrollController,
                    scrollDirection: Axis.horizontal,
                    padding: const EdgeInsets.only(bottom: 14),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        for (var i = 0; i < segments.length; i++)
                          Padding(
                            padding: const EdgeInsets.only(right: 4),
                            child: _TimelineSegment(
                              segment: segments[i],
                              width: segments[i]
                                  .flex
                                  .toDouble()
                                  .clamp(60.0, 120.0),
                              selected: selectedIndex == i,
                              showEndLabel: i == segments.length - 1,
                              onTap: () => setState(() => _selectedSeg = i),
                            ),
                          ),
                      ],
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                '구간을 탭해서 상세 분석을 확인하세요',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 12, color: AppColors.gray400),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),

        // Selected segment
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: seg.level.color.withValues(alpha: 0.03),
            border: Border.all(color: seg.level.color.withValues(alpha: 0.25)),
            borderRadius: BorderRadius.circular(16),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    '${seg.time} 상세',
                    style: const TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.bold,
                      color: AppColors.gray900,
                    ),
                  ),
                  StatusBadge(
                    label: seg.level.label,
                    background: seg.level.badgeBg,
                    foreground: seg.level.badgeFg,
                  ),
                ],
              ),
              const SizedBox(height: 12),
              GridView.count(
                crossAxisCount: 3,
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                mainAxisSpacing: 8,
                crossAxisSpacing: 8,
                childAspectRatio: 1.5,
                children: [
                  _statTile(seg.scoreLabel, seg.score, seg.scoreColor),
                  _statTile('발표 속도', seg.speed, AppColors.gray900),
                  _statTile('음성 톤', seg.tone, AppColors.gray900),
                  _statTile('멈춤 횟수', seg.pause, AppColors.gray900),
                  _statTile('추임새', seg.filler, AppColors.gray900),
                  _statTile('반복', seg.repeat, AppColors.gray900),
                ],
              ),
              const SizedBox(height: 12),
              _whiteBox(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      '확인된 신호',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: AppColors.gray700,
                      ),
                    ),
                    const SizedBox(height: 8),
                    for (final s in seg.signals)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 4),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('•',
                                style: TextStyle(
                                    fontSize: 12, color: seg.level.color)),
                            const SizedBox(width: 6),
                            Expanded(
                              child: Text(
                                s,
                                style: const TextStyle(
                                  fontSize: 12,
                                  height: 1.5,
                                  color: AppColors.gray600,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                  ],
                ),
              ),
              if (seg.postureAvailable) ...[
                const SizedBox(height: 12),
                Align(
                  alignment: Alignment.centerLeft,
                  child: Text(
                    '자세 신호',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: AppColors.gray700,
                    ),
                  ),
                ),
                const SizedBox(height: 8),
                if (!seg.postureSignalSufficient)
                  const Align(
                    alignment: Alignment.centerLeft,
                    child: Text(
                      '자세 신호 부족',
                      style: TextStyle(fontSize: 12, color: AppColors.gray500),
                    ),
                  )
                else ...[
                  GridView.count(
                    crossAxisCount: 2,
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    mainAxisSpacing: 8,
                    crossAxisSpacing: 8,
                    childAspectRatio: 1.8,
                    children: [
                      _statTile('어깨 기울기', seg.shoulderTilt, AppColors.gray900),
                      _statTile('고개 숙임', seg.headDown, AppColors.gray900),
                      _statTile('상체 기울기', seg.torsoLean, AppColors.gray900),
                      _statTile('상체 방향', seg.torsoLeanDirection, AppColors.gray900),
                      _statTile('자세 개방성', seg.openPosture, AppColors.gray900),
                      _statTile('제스처 파워존', seg.powerZone, AppColors.gray900),
                      _statTile('머리 정렬', seg.headAlignment, AppColors.gray900),
                      _statTile('제스처 활동성', seg.gestureActivity, AppColors.gray900),
                    ],
                  ),
                  if (seg.postureReasons.isNotEmpty) ...[
                    const SizedBox(height: 12),
                    _whiteBox(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          for (final reason in seg.postureReasons)
                            Padding(
                              padding: const EdgeInsets.only(bottom: 4),
                              child: Row(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text('•',
                                      style: TextStyle(
                                          fontSize: 12, color: seg.level.color)),
                                  const SizedBox(width: 6),
                                  Expanded(
                                    child: Text(
                                      reason,
                                      style: const TextStyle(
                                        fontSize: 12,
                                        height: 1.5,
                                        color: AppColors.gray600,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                        ],
                      ),
                    ),
                  ],
                ],
              ],
              const SizedBox(height: 12),
              _whiteBox(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      '해당 구간 발표 내용',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: AppColors.gray700,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      seg.script,
                      style: const TextStyle(
                        fontSize: 12,
                        height: 1.6,
                        color: AppColors.gray600,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _statTile(String label, String value, Color color) {
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: AppColors.white,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(label,
              style: const TextStyle(fontSize: 11, color: AppColors.gray500)),
          const SizedBox(height: 2),
          Text(
            value,
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.bold,
              color: color,
            ),
          ),
        ],
      ),
    );
  }

  Widget _whiteBox({required Widget child}) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.white,
        borderRadius: BorderRadius.circular(12),
      ),
      child: child,
    );
  }

  Widget _improveTab() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: AppColors.green50,
            border: Border.all(color: AppColors.green100),
            borderRadius: BorderRadius.circular(16),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                '잘한 점',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                  color: AppColors.green800,
                ),
              ),
              const SizedBox(height: 8),
              for (final line in widget.strengths)
                Padding(
                  padding: const EdgeInsets.only(bottom: 4),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('• ',
                          style: TextStyle(
                              fontSize: 12, color: AppColors.green700)),
                      Expanded(
                        child: Text(
                          line,
                          style: const TextStyle(
                            fontSize: 12,
                            height: 1.5,
                            color: AppColors.green700,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: AppColors.violet50,
            border: Border.all(color: AppColors.violet100),
            borderRadius: BorderRadius.circular(16),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                '한 줄 코칭',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                  color: AppColors.violet800,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                widget.oneLineCoaching,
                style: const TextStyle(
                  fontSize: 14,
                  height: 1.6,
                  fontWeight: FontWeight.w500,
                  color: AppColors.violet700,
                ),
              ),
            ],
          ),
        ),
        if (widget.improvements.isNotEmpty) ...[
          const SizedBox(height: 16),
          AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  '개선할 점',
                  style: TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.bold,
                    color: AppColors.gray900,
                  ),
                ),
                const SizedBox(height: 12),
                for (final entry in widget.improvements.asMap().entries)
                  Padding(
                    padding: EdgeInsets.only(
                      bottom: entry.key == widget.improvements.length - 1 ? 0 : 14,
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '${entry.key + 1}. ${entry.value['title'] ?? ''}',
                          style: const TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                            color: AppColors.gray900,
                          ),
                        ),
                        if ((entry.value['time_range'] ?? '').toString().isNotEmpty) ...[
                          const SizedBox(height: 2),
                          Text(
                            entry.value['time_range'].toString(),
                            style: const TextStyle(fontSize: 11, color: AppColors.gray400),
                          ),
                        ],
                        const SizedBox(height: 4),
                        Text(
                          entry.value['description']?.toString() ?? '',
                          style: const TextStyle(
                            fontSize: 12,
                            height: 1.5,
                            color: AppColors.gray600,
                          ),
                        ),
                      ],
                    ),
                  ),
              ],
            ),
          ),
        ],
        if (widget.practiceGoals.isNotEmpty) ...[
          const SizedBox(height: 16),
          AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  '다음 연습 목표',
                  style: TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.bold,
                    color: AppColors.gray900,
                  ),
                ),
                const SizedBox(height: 12),
                for (final entry in widget.practiceGoals.asMap().entries)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Text(
                      '${entry.key + 1}. ${entry.value}',
                      style: const TextStyle(
                        fontSize: 12,
                        height: 1.5,
                        color: AppColors.gray600,
                      ),
                    ),
                  ),
              ],
            ),
          ),
        ],
      ],
    );
  }

  Widget _scriptTab() {
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                '발표 내용 스크립트',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                  color: AppColors.gray900,
                ),
              ),
              GestureDetector(
                onTap: _copyScript,
                child: _copied
                    ? const Text(
                        '복사됨!',
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w500,
                          color: AppColors.violet600,
                        ),
                      )
                    : const Icon(Icons.copy_outlined,
                        size: 18, color: AppColors.gray400),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            widget.fullScript,
            style: const TextStyle(
              fontSize: 12,
              height: 1.7,
              color: AppColors.gray600,
            ),
          ),
        ],
      ),
    );
  }
}

class _TimeLabel extends StatelessWidget {
  const _TimeLabel(this.text);

  final String text;

  @override
  Widget build(BuildContext context) {
    return Text(
      text,
      style: const TextStyle(fontSize: 12, color: AppColors.gray400),
    );
  }
}

class _TimelineSegment extends StatelessWidget {
  const _TimelineSegment({
    required this.segment,
    required this.width,
    required this.selected,
    required this.showEndLabel,
    required this.onTap,
  });

  final Segment segment;
  final double width;
  final bool selected;
  final bool showEndLabel;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final times = segment.time.split(' ~ ');

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(8),
          child: GestureDetector(
            onTap: onTap,
            child: Container(
              width: width,
              height: 40,
              decoration: BoxDecoration(
                color: segment.level.color,
                border: selected
                    ? Border.all(
                        color: AppColors.white.withValues(alpha: 0.6),
                        width: 2,
                      )
                    : null,
              ),
              child: Center(
                child: Text(
                  segment.level.label,
                  style: const TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                    color: AppColors.white,
                  ),
                ),
              ),
            ),
          ),
        ),
        const SizedBox(height: 4),
        SizedBox(
          width: width,
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              _TimeLabel(times.first),
              if (showEndLabel) _TimeLabel(times.last),
            ],
          ),
        ),
      ],
    );
  }
}
