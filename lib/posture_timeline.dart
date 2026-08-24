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
      windowIndex: json['window_index'] as int? ?? 0,
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
        separatorBuilder: (_, _) => const SizedBox(width: 4),
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
