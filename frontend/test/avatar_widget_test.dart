import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pr_front/posture/avatar_widget.dart';

void main() {
  testWidgets('shows idle emoji by default', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: AvatarWidget(state: 'idle')),
    );

    expect(find.text('💤'), findsOneWidget);
  });

  testWidgets('shows bored emoji for bored state', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: AvatarWidget(state: 'bored')),
    );

    expect(find.text('😴'), findsOneWidget);
  });

  testWidgets('shows unknown emoji for unknown state', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: AvatarWidget(state: 'unknown')),
    );

    expect(find.text('❔'), findsOneWidget);
  });

  testWidgets('falls back to idle emoji for an unrecognized state string', (
    tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(home: AvatarWidget(state: 'nonsense')),
    );

    expect(find.text('💤'), findsOneWidget);
  });
}
