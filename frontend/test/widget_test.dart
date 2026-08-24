import 'package:flutter_test/flutter_test.dart';
import 'package:pr_front/main.dart';

void main() {
  testWidgets(
    '홈 화면이 정상적으로 표시된다',
    (WidgetTester tester) async {
      await tester.pumpWidget(
        const PresentationCoachApp(),
      );

      expect(
        find.text('AI Presentation Coach'),
        findsOneWidget,
      );

      expect(
        find.text('발표 녹음 시작'),
        findsOneWidget,
      );

      expect(
        find.text('WAV 파일 업로드'),
        findsOneWidget,
      );
    },
  );
}