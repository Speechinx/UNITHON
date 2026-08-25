import 'package:flutter/material.dart';

class AvatarWidget extends StatelessWidget {
  const AvatarWidget({
    super.key,
    required this.state,
  });

  final String state;

  static const Map<String, String> _emojiByState = {
    'idle': '💤',
    'good': '🙂',
    'bad': '😟',
    'unknown': '❔',
  };

  static const Map<String, Color> _colorByState = {
    'idle': Colors.grey,
    'good': Colors.green,
    'bad': Colors.red,
    'unknown': Colors.grey,
  };

  @override
  Widget build(BuildContext context) {
    final emoji = _emojiByState[state] ?? _emojiByState['idle']!;
    final color = _colorByState[state] ?? _colorByState['idle']!;

    return AnimatedSwitcher(
      duration: const Duration(milliseconds: 300),
      transitionBuilder: (child, animation) {
        return ScaleTransition(scale: animation, child: child);
      },
      child: Container(
        key: ValueKey(state),
        width: 96,
        height: 96,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: color.withOpacity(0.12),
          border: Border.all(color: color, width: 2),
        ),
        alignment: Alignment.center,
        child: Text(
          emoji,
          style: const TextStyle(fontSize: 48),
        ),
      ),
    );
  }
}
