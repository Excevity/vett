#!/bin/bash
# No-root setup: static ffmpeg + Kokoro TTS model + python libs.
# Honors VETT_TOOLS (defaults to ~/tools) so it works locally AND in CI.
set -e
TOOLS="${VETT_TOOLS:-$HOME/tools}"
mkdir -p "$TOOLS" && cd "$TOOLS"

# ffmpeg / ffprobe (static) — skip if ffmpeg is already on PATH (e.g. apt in CI)
if [ ! -f ffmpeg ] && ! command -v ffmpeg >/dev/null 2>&1; then
  curl -fsSL --retry 3 https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz -o ff.tar.xz
  tar xf ff.tar.xz
  mv ffmpeg-*-static/ffmpeg ffmpeg-*-static/ffprobe .
  rm -rf ffmpeg-*-static ff.tar.xz
fi

# Kokoro v1.0 model + voices (natural TTS). -f so a bad HTTP response errors
# instead of saving an unusable file; --retry rides out transient blips.
mkdir -p kokoro && cd kokoro
KB="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"
[ -f kokoro.onnx ] || curl -fsSL --retry 3 "$KB/kokoro-v1.0.onnx" -o kokoro.onnx
[ -f voices.bin ]  || curl -fsSL --retry 3 "$KB/voices-v1.0.bin"  -o voices.bin
cd ..

# python libs (user space, no root)
python3 -m pip install --user --break-system-packages \
  Pillow numpy onnxruntime kokoro-onnx soundfile \
  google-api-python-client google-auth-httplib2 google-auth-oauthlib
echo "setup done. tools in $TOOLS"
