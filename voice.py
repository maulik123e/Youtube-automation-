"""Free voiceover via Microsoft Edge neural voices (edge-tts).

Streams audio AND per-word boundary events, so we get exact word timings
for word-by-word karaoke captions — the CapCut look — at zero cost.
"""
import asyncio
import json

import edge_tts

from config import TTS_VOICE, TTS_RATE, WORK_DIR, ensure_dirs


async def _synth(text: str, mp3_path: str) -> list[dict]:
    words = []
    communicate = edge_tts.Communicate(text, TTS_VOICE, rate=TTS_RATE,
                                       boundary="WordBoundary")
    with open(mp3_path, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                # offset/duration are in 100-nanosecond units
                words.append({
                    "word": chunk["text"],
                    "start": float(chunk["offset"]) / 10_000_000,
                    "duration": float(chunk["duration"]) / 10_000_000,
                })
    return words


def synthesize(text: str, slug: str) -> tuple[str, list[dict]]:
    """Return (mp3_path, word_timings)."""
    ensure_dirs()
    mp3 = str(WORK_DIR / f"{slug}.mp3")
    words = asyncio.run(_synth(text, mp3))
    if not words:
        raise RuntimeError("TTS produced no word timings — check your network.")
    return mp3, words


def audio_duration(mp3_path: str) -> float:
    import subprocess, re
    out = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", mp3_path], capture_output=True, text=True)
    return float(out.stdout.strip())


if __name__ == "__main__":
    mp3, words = synthesize("This is a test of the free voice system.", "test")
    print(f"saved {mp3} with {len(words)} timed words")
    print(json.dumps(words[:5], indent=2))
