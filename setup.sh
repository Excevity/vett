#!/bin/bash
# No-root setup: static ffmpeg, Piper TTS + voice, python libs (user space).
set -e
mkdir -p ~/tools && cd ~/tools
[ -f ffmpeg ] || { curl -sSL https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz -o ff.tar.xz; tar xf ff.tar.xz; mv ffmpeg-*-static/ffmpeg ffmpeg-*-static/ffprobe .; rm -rf ffmpeg-*-static ff.tar.xz; }
[ -d piper ] || { curl -sSL https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_linux_x86_64.tar.gz -o p.tgz; tar xf p.tgz; rm p.tgz; }
mkdir -p piper/voices && cd piper/voices
b="https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium"
[ -f amy.onnx ] || curl -sSL "$b/en_US-amy-medium.onnx" -o amy.onnx
[ -f amy.onnx.json ] || curl -sSL "$b/en_US-amy-medium.onnx.json" -o amy.onnx.json
python3 -m pip install --user --break-system-packages Pillow numpy
echo "setup done."
