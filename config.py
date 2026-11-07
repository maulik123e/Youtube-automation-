"""Central config. Everything here is FREE — see .env.example for key setup."""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:                      # .env support optional
    def load_dotenv(*_a, **_k):
        pass

BASE_DIR = Path(__file__).parent
WORK_DIR = BASE_DIR / "work"          # per-video scratch (audio, captions...)
ASSETS_DIR = BASE_DIR / "assets"
OUT_DIR = BASE_DIR / "out"            # finished mp4s
LOGS_DIR = BASE_DIR / "logs"

load_dotenv(BASE_DIR / ".env")

# LLM (OpenAI-compatible, works with Gemini/Groq/Ollama free tiers)
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.0-flash")

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")

TTS_VOICE = os.getenv("TTS_VOICE", "en-US-AndrewNeural")
TTS_RATE = os.getenv("TTS_RATE", "+8%")

NICHES = [n.strip() for n in os.getenv(
    "NICHES", "psychology facts,space facts,money facts").split(",")]

VIDEO_W, VIDEO_H = 1080, 1920         # vertical 9:16
FPS = 30

# Bold caption style (CapCut-ish)
CAPTION_FONT_SIZE = 72
CAPTION_COLOR_SPOKEN = "&H0000FFFF"   # yellow (ASS BGR)
CAPTION_COLOR_UNSPOKEN = "&H00FFFFFF" # white
CAPTION_OUTLINE = "&H00141414"


def ensure_dirs():
    for d in (WORK_DIR, ASSETS_DIR, OUT_DIR, LOGS_DIR):
        d.mkdir(parents=True, exist_ok=True)


def find_bold_font() -> str:
    """Locate a bold TTF on this machine (Linux/Mac/Windows fallbacks)."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    # last resort: any bold ttf on the system
    for root in ("/usr/share/fonts", "/usr/local/share/fonts"):
        for dirpath, _, files in os.walk(root):
            for f in files:
                if f.lower().endswith(".ttf") and "bold" in f.lower():
                    return os.path.join(dirpath, f)
    raise FileNotFoundError("No bold TTF font found. Set one in video.py.")
