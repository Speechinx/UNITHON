import 'package:flutter_test/flutter_test.dart';
import 'package:pr_front/main.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('홈 화면이 정상적으로 표시된다', (WidgetTester tester) async {
    await tester.pumpWidget(const PresentationCoachApp());
    await tester.pump();

    expect(find.text('Speechinx'), findsOneWidget);
    expect(find.text('발표 준비가 되셨나요?'), findsOneWidget);
    expect(find.text('파일 업로드'), findsOneWidget);
  });
}
