"""Assemble the vertical Short: background + voiceover + karaoke captions.

Background priority:
1. Pexels stock video matching the topic (free API key, looks pro)
2. Procedural gradient (always works, offline, still looks clean)

Captions: ASS subtitles with karaoke tags -> spoken words turn yellow
exactly when voiced. This is the #1 retention trick for shorts.
"""
import json
import math
import re
import subprocess
from pathlib import Path

import requests

from config import (ASSETS_DIR, OUT_DIR, PEXELS_API_KEY, VIDEO_W, VIDEO_H,
                    FPS, CAPTION_FONT_SIZE, CAPTION_COLOR_SPOKEN,
                    CAPTION_COLOR_UNSPOKEN, CAPTION_OUTLINE, WORK_DIR,
                    ensure_dirs, find_bold_font)


# ---------------------------------------------------------------- background

def fetch_pexels_video(query: str, slug: str, min_w=600) -> str | None:
    """Download a ~vertical stock clip. Returns path or None."""
    if not PEXELS_API_KEY:
        return None
    try:
        r = requests.get(
            "https://api.pexels.com/videos/search",
            headers={"Authorization": PEXELS_API_KEY},
            params={"query": query, "orientation": "portrait",
                    "size": "medium", "per_page": 5},
            timeout=20)
        for v in r.json().get("videos", []):
            best = None
            for f in v.get("video_files", []):
                w = f.get("width") or 0
                if w >= min_w and (best is None or abs(w - 720) < abs(best["width"] - 720)):
                    best = f
            if best:
                out = WORK_DIR / f"{slug}_bg.mp4"
                with requests.get(best["link"], timeout=60, stream=True) as dl:
                    dl.raise_for_status()
                    with open(out, "wb") as f:
                        for ch in dl.iter_content(1 << 16):
                            f.write(ch)
                return str(out)
    except Exception as e:
        print(f"  [warn] Pexels fetch failed ({e}); using gradient background.")
    return None


def make_gradient_image(slug: str) -> str:
    """Navy->violet gradient with a soft glow, made with ffmpeg (no PIL)."""
    out = WORK_DIR / f"{slug}_bg.png"
    w, h = VIDEO_W, VIDEO_H
    subprocess.run([
        "ffmpeg", "-y", "-v", "quiet",
        "-f", "lavfi", "-i",
        f"gradients=size={w}x{h}:rate=30:nb_colors=3:"
        "c0=0x0b1026:c1=0x3b1d5e:c2=0x101a3a",
        "-frames:v", "1", str(out)], check=True)
    return str(out)


# ----------------------------------------------------------------- captions

def _fmt_ass_time(sec: float) -> str:
    cs = max(0, round(sec * 100))
    h, rem = divmod(cs, 360000)
    m, rem = divmod(rem, 6000)
    s, c = divmod(rem, 100)
    return f"{h}:{m:02d}:{s:02d}.{c:02d}"


def _norm(w: str) -> str:
    return re.sub(r"[^a-z0-9']", "", w.lower())


def match_words_to_lines(script_lines: list[str], words: list[dict]) -> list[dict]:
    """Assign each timed word to a script line (tolerant two-pointer match)."""
    stream = [_norm(w["word"]) for w in words]
    captions = []
    pos = 0
    for line in script_lines:
        lw = line.split()
        starts, durs, texts = [], [], []
        for token in lw:
            key = _norm(token)
            idx = -1
            for j in range(pos, len(stream)):
                if stream[j] == key:
                    idx = j
                    break
            if idx == -1:  # word not heard (TTS contraction) -> keep timing loose
                w = words[min(pos, len(words) - 1)]
                starts.append(w["start"] + w["duration"])
                durs.append(max(w["duration"], 0.12))
            else:
                starts.append(words[idx]["start"])
                durs.append(max(words[idx]["duration"], 0.12))
                pos = idx + 1
            texts.append(token)
        if texts:
            captions.append({"text": " ".join(texts),
                             "start": starts[0],
                             "end": max(starts[-1] + durs[-1], starts[0] + 0.25)})
            captions[-1]["words"] = texts
            captions[-1]["word_starts"] = starts
            captions[-1]["word_durs"] = durs
    return captions


def _font_family(font_path: str) -> str:
    """Get the family name libass will match (e.g. 'DejaVu Sans')."""
    import subprocess
    try:
        out = subprocess.run(
            ["fc-query", "--format=%{family}", font_path],
            capture_output=True, text=True, timeout=10)
        fam = out.stdout.split(",")[0].strip()
        if fam:
            return fam
    except Exception:
        pass
    # heuristic fallback: strip 'Bold' from filename
    stem = Path(font_path).stem
    return re.sub(r"[-_ ]?bold$", "", stem).strip() or stem


def write_ass(captions: list[dict], ass_path: str):
    """Karaoke ASS: upcoming words white, spoken words yellow."""
    family = _font_family(find_bold_font())
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {VIDEO_W}
PlayResY: {VIDEO_H}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{family},{CAPTION_FONT_SIZE},{CAPTION_COLOR_SPOKEN},{CAPTION_COLOR_UNSPOKEN},{CAPTION_OUTLINE},&H80000000,1,0,0,0,100,100,0.6,0,1,4,1,2,60,60,420,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    # Put the real font file where libass/fontconfig will find it by family name
    lines = []
    for c in captions:
        k_parts = []
        for t, st, du in zip(c["words"], c["word_starts"], c["word_durs"]):
            cs = max(1, round(du * 100))
            k_parts.append(f"{{\\k{cs}}}{t}")
        text = " ".join(k_parts)
        lines.append(
            f"Dialogue: 0,{_fmt_ass_time(c['start'])},{_fmt_ass_time(c['end'])},"
            f"Cap,,0,0,0,,{text}")
    Path(ass_path).write_text(header + "\n".join(lines) + "\n", encoding="utf-8")


# ------------------------------------------------------------------ assembly

def build_video(mp3_path: str, script: dict, words: list[dict],
                slug: str, bg_query: str) -> str:
    ensure_dirs()
    captions = match_words_to_lines(script["lines"], words)
    ass_path = str(WORK_DIR / f"{slug}.ass")
    write_ass(captions, ass_path)

    bg_video = fetch_pexels_video(bg_query, slug)
    duration = json.loads(subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "json", mp3_path], capture_output=True, text=True).stdout
    )["format"]["duration"]

    # make the bold font discoverable by libass via fontsdir
    font_dir = ASSETS_DIR / "fonts"
    font_dir.mkdir(parents=True, exist_ok=True)
    src_font = find_bold_font()
    dst_font = font_dir / Path(src_font).name
    if not dst_font.exists():
        import shutil
        shutil.copy(src_font, dst_font)

    out_path = OUT_DIR / f"{slug}.mp4"
    if bg_video:
        vfilter = (f"scale={VIDEO_W}:{VIDEO_H}:force_original_aspect_ratio=increase,"
                   f"crop={VIDEO_W}:{VIDEO_H},eq=brightness=-0.12:saturation=1.1")
        bg_in = ["-stream_loop", "-1", "-i", bg_video]
    else:
        png = make_gradient_image(slug)
        frames = math.ceil(float(duration) * FPS) + FPS
        vfilter = (f"zoompan=z='min(zoom+0.0009,1.25)':x='iw/2-(iw/zoom/2)':"
                   f"y='ih/2-(ih/zoom/2)':d={frames}:s={VIDEO_W}x{VIDEO_H}:fps={FPS}")
        bg_in = ["-loop", "1", "-i", png]

    cmd = [
        "ffmpeg", "-y", "-v", "warning",
        *bg_in, "-i", mp3_path,
        "-filter_complex",
        f"[0:v]{vfilter}[bg];"
        f"[bg]subtitles={ass_path}:fontsdir='{font_dir}',"
        f"format=yuv420p[v];[1:a]loudnorm=I=-14:TP=-1.5[a]",
        "-map", "[v]", "-map", "[a]",
        "-t", duration, "-r", str(FPS),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
        "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart",
        str(out_path),
    ]
    subprocess.run(cmd, check=True)
    return str(out_path)


if __name__ == "__main__":
    print("video.py is driven by main.py — run: python3 main.py make --topic 'why you dream in your mother tongue'")
