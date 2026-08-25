#!/usr/bin/env bash
# Render Static Site build command.
# Render's static-site build image has no Flutter/Dart SDK preinstalled,
# so this fetches the exact stable version used for local development,
# then builds the web release.
set -euo pipefail

FLUTTER_VERSION="3.47.1"

if [ ! -d flutter-sdk ]; then
  git clone https://github.com/flutter/flutter.git --depth 1 \
    --branch "${FLUTTER_VERSION}" flutter-sdk
fi

export PATH="$PATH:$(pwd)/flutter-sdk/bin"

flutter --version
flutter pub get
flutter build web --release
