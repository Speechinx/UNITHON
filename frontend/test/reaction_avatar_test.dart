import 'package:flutter_test/flutter_test.dart';
import 'package:pr_front/posture/reaction_avatar.dart';

void main() {
  test('returns the asset path for states that have a reaction video', () {
    expect(reactionAssetForState('engaged'), 'assets/reactions/engaged.mp4');
    expect(reactionAssetForState('focused'), 'assets/reactions/focused.mp4');
    expect(reactionAssetForState('confused'), 'assets/reactions/confused.mp4');
  });

  test('returns null for states without a reaction video', () {
    expect(reactionAssetForState('bored'), null);
    expect(reactionAssetForState('unknown'), null);
    expect(reactionAssetForState('idle'), null);
    expect(reactionAssetForState('nonsense'), null);
  });
}
