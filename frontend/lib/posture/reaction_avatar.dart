import 'package:flutter/material.dart';
import 'package:video_player/video_player.dart';

import 'avatar_widget.dart';

/// avatar_state별 반응 영상 asset 경로. 매핑에 없는 상태는
/// [AvatarWidget] 이모지 폴백으로 처리된다.
const Map<String, String> reactionVideoAssets = {
  'engaged': 'assets/reactions/engaged.mp4',
  'focused': 'assets/reactions/focused.mp4',
  'confused': 'assets/reactions/confused.mp4',
  'bored': 'assets/reactions/bored.mp4',
};

String? reactionAssetForState(String state) {
  return reactionVideoAssets[state];
}

/// 자세 상태(avatar_state)에 따라 반응 영상을 루프 재생하는 위젯.
/// 부모가 준 사각형 영역을 꽉 채워서 재생하며, 반응 영상이 없는 상태거나
/// 로딩 중이면 [AvatarWidget] 이모지로 폴백한다.
class ReactionAvatar extends StatefulWidget {
  const ReactionAvatar({
    super.key,
    required this.state,
  });

  final String state;

  @override
  State<ReactionAvatar> createState() => _ReactionAvatarState();
}

class _ReactionAvatarState extends State<ReactionAvatar> {
  VideoPlayerController? _controller;
  String? _loadedAsset;

  @override
  void initState() {
    super.initState();
    _syncController();
  }

  @override
  void didUpdateWidget(covariant ReactionAvatar oldWidget) {
    super.didUpdateWidget(oldWidget);

    if (oldWidget.state != widget.state) {
      _syncController();
    }
  }

  void _syncController() {
    final asset = reactionAssetForState(widget.state);

    if (asset == _loadedAsset) {
      return;
    }

    final previous = _controller;
    _controller = null;
    _loadedAsset = asset;
    previous?.dispose();

    if (asset == null) {
      setState(() {});
      return;
    }

    final controller = VideoPlayerController.asset(asset);
    _controller = controller;

    controller
        .initialize()
        .then((_) {
          if (!mounted || _controller != controller) {
            return;
          }

          controller
            ..setLooping(true)
            ..play();

          setState(() {});
        })
        .catchError((Object _) {
          if (!mounted || _controller != controller) {
            return;
          }

          controller.dispose();

          setState(() {
            _controller = null;
          });
        });
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final controller = _controller;

    if (controller == null || !controller.value.isInitialized) {
      return Center(child: AvatarWidget(state: widget.state));
    }

    return SizedBox.expand(
      child: FittedBox(
        fit: BoxFit.cover,
        child: SizedBox(
          width: controller.value.size.width,
          height: controller.value.size.height,
          child: VideoPlayer(controller),
        ),
      ),
    );
  }
}
