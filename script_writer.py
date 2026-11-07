"""Write the Short's script with a free LLM (Gemini / Groq / Ollama).

Structure enforced by the prompt — proven Shorts formula:
0-2s hook -> open loop -> 3-5 rapid value beats -> payoff -> loop/replay bait.
Falls back to a built-in template if no LLM key is configured yet, so the
pipeline always runs end-to-end.
"""
import json
import re

from openai import OpenAI

from config import LLM_BASE_URL, LLM_API_KEY, LLM_MODEL

SYSTEM = """You are a YouTube Shorts scriptwriter who has written hundreds of viral shorts.
Write in plain spoken English: short punchy sentences, contractions, zero fluff.
Hard rules:
- Total length 130-165 words (about 35-45 seconds spoken).
- The FIRST line must be a pattern-interrupt hook under 8 words that creates an open loop.
- Then deliver 3-5 surprising, specific value beats. Concrete numbers and facts beat vibes.
- End with a payoff line + one casual CTA to follow (no begging).
- Output STRICT JSON only, no markdown fences, with keys:
  "title" (max 70 chars, curiosity-driven), "lines" (list of spoken lines),
  "description" (2 sentences + 5 #hashtags), "tags" (10 lowercase tags).
"""


def write_script(topic: str, niche: str = "") -> dict:
    prompt = f"Niche: {niche or 'general'}. Topic/angle to cover: {topic}"
    if LLM_BASE_URL and LLM_API_KEY:
        client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "system", "content": SYSTEM},
                      {"role": "user", "content": prompt}],
            temperature=0.9, max_tokens=900)
        text = resp.choices[0].message.content.strip()
        # tolerate accidental ```json fences
        text = re.sub(r"^```(json)?|```$", "", text, flags=re.MULTILINE).strip()
        return json.loads(text)
    print("[script] no LLM key configured -> built-in template fallback.")
    return _fallback_script(topic)


def _fallback_script(topic: str) -> dict:
    """Works offline: structures your input into the proven beats."""
    words = topic.split()
    subject = " ".join(words[:6]).title() if words else "This"
    slug = re.sub(r"[^a-z0-9]+", "", topic.lower())[:12] or "facts"
    lines = [
        f"Stop scrolling - this changes how you see {subject.lower()}.",
        f"Here is the thing nobody tells you about {topic.lower()}.",
        "Most people get this completely backwards, and it costs them.",
        "The surprising part? It takes under a minute to understand.",
        "Once you see it, you cannot unsee it.",
        "Follow for more - the next one goes even deeper.",
    ]
    return {
        "title": f"{subject}: the 40-second version 👀"[:70],
        "lines": lines,
        "description": f"{subject}, explained fast. Follow for daily shorts like this. "
                       f"#shorts #{slug} #facts #didyouknow #learnontiktok",
        "tags": [slug, "shorts", "facts", "didyouknow", "viral", "learning",
                 "quickfacts", "reels", "fyp", "education"],
    }


def save_script(script: dict, slug: str):
    from config import WORK_DIR, ensure_dirs
    ensure_dirs()
    path = WORK_DIR / f"{slug}.script.json"
    path.write_text(json.dumps(script, indent=2))
    return path


def spoken_text(script: dict) -> str:
    """Join spoken lines into one TTS-ready string."""
    return " ".join(script["lines"])
