import os
# Portable: env overrides let the same code run on your machine AND in CI.
TOOLS   = os.environ.get("VETT_TOOLS", os.path.expanduser("~/tools"))
FFMPEG  = os.environ.get("FFMPEG",  os.path.join(TOOLS, "ffmpeg"))
FFPROBE = os.environ.get("FFPROBE", os.path.join(TOOLS, "ffprobe"))
# legacy Piper (kept for fallback; Kokoro is the default voice engine)
PIPER       = os.path.join(TOOLS, "piper", "piper")
PIPER_VOICE = os.path.join(TOOLS, "piper", "voices", "amy.onnx")
KOKORO_MODEL  = os.environ.get("KOKORO_MODEL",  os.path.join(TOOLS, "kokoro", "kokoro.onnx"))
KOKORO_VOICES = os.environ.get("KOKORO_VOICES", os.path.join(TOOLS, "kokoro", "voices.bin"))
KOKORO_VOICE_CHOICES = ["am_michael", "am_adam", "am_onyx", "af_heart", "af_bella"]
VOICE = os.environ.get("VETT_VOICE", "am_onyx")   # user's pick
FONT_DIR = os.environ.get("FONT_DIR", "/usr/share/fonts/truetype/dejavu")

# Story data: prefer explicit env, then this repo's own data/, then the local
# hl_copybot scan if present. scan.py writes the repo-local one (used in CI).
_repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_local_scan = os.path.join(_repo, "data", "leaderboard_scan.json")
_bot_scan = "/home/mrrobot/hl_copybot/data/leaderboard_scan.json"
SCANNER_DATA = os.environ.get("VETT_SCAN") or (
    _local_scan if os.path.exists(_local_scan) else
    (_bot_scan if os.path.exists(_bot_scan) else _local_scan))
