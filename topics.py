"""Find proven viral topics by scoring recent shorts in your niche.

Free method: yt-dlp reads YouTube search results (no API key needed).
Scoring = views weighted by recency, so fresh viral hits rank on top.
IMPORTANT: we borrow the *topic/angle*, never copy another creator's video.
"""
import json
import re
import time

import yt_dlp

from config import WORK_DIR, NICHES, ensure_dirs

MAX_AGE_DAYS = 21          # only care about the last 3 weeks
MIN_VIEWS = 50_000         # ignore small hits


def _age_days(upload_date: str | None) -> float:
    """upload_date is YYYYMMDD; return age in days."""
    if not upload_date:
        return MAX_AGE_DAYS  # unknown age -> least interesting
    from datetime import datetime, timezone
    try:
        d = datetime.strptime(upload_date, "%Y%m%d").replace(tzinfo=timezone.utc)
        return max((datetime.now(timezone.utc) - d).total_seconds() / 86400, 0.5)
    except ValueError:
        return MAX_AGE_DAYS


def score(entry: dict) -> float:
    """Viral score: views decayed by age. 200k views in 2 days > 2M in 2 years."""
    views = entry.get("view_count") or 0
    age = _age_days(entry.get("upload_date"))
    if age > MAX_AGE_DAYS or views < MIN_VIEWS:
        return 0.0
    return views / (age ** 1.35)


def fetch_shorts(niche: str, limit: int = 20) -> list[dict]:
    """Pull recent short-form candidates for a niche."""
    opts = {
        "quiet": True, "noplaylist": True, "skip_download": True,
        "extract_flat": False,
        # short-form filter: prefer <3 min so we catch Shorts + vertical vids
        "match_filter": yt_dlp.utils.match_filter_func("duration<180"),
    }
    candidates = []
    with yt_dlp.YoutubeDL(opts) as ydl:
        for query in (f"{niche} shorts", f"{niche} #shorts"):
            try:
                info = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)
            except Exception as e:
                print(f"  [warn] search '{query}' failed: {e}")
                continue
            for e in info.get("entries") or []:
                if not e or e.get("view_count") is None:
                    continue
                candidates.append({
                    "title": e.get("title", "").strip(),
                    "url": e.get("webpage_url") or e.get("url"),
                    "channel": e.get("channel") or e.get("uploader") or "?",
                    "views": e.get("view_count") or 0,
                    "age_days": round(_age_days(e.get("upload_date")), 1),
                    "duration": e.get("duration") or 0,
                    "niche": niche,
                })
            time.sleep(1.5)  # be polite to YouTube
    # dedupe by title similarity (keep highest views)
    seen, deduped = set(), []
    for c in sorted(candidates, key=lambda x: -x["views"]):
        key = re.sub(r"[^a-z0-9 ]", "", c["title"].lower())[:40]
        if key and key not in seen:
            seen.add(key)
            deduped.append(c)
    for c in deduped:
        c["score"] = round(score(c), 1)
    return sorted((c for c in deduped if c["score"] > 0),
                  key=lambda x: -x["score"])


def find_topics(niches: list[str] | None = None, per_niche: int = 5) -> list[dict]:
    niches = niches or NICHES
    all_hits = []
    for niche in niches:
        print(f"Scoring recent shorts in '{niche}' ...")
        all_hits.extend(fetch_shorts(niche)[:per_niche])
    ranked = sorted(all_hits, key=lambda x: -x["score"])
    if not ranked:
        print("[topics] no live results (offline?) — evergreen topic bank.")
        ranked = offline_topics()
    ensure_dirs()
    (WORK_DIR / "topics.json").write_text(json.dumps(ranked, indent=2))
    return ranked


def suggest_angle(hit: dict) -> str:
    """Turn a proven topic into a fresh angle for YOUR video."""
    t = re.sub(r"#\w+|\|.*$", "", hit["title"]).strip(" -:")
    return t


# Evergreen proven formats — used when YouTube is unreachable (offline/
# sandboxed networks), so the pipeline never dies, just loses live scoring.
EVERGREEN_TOPICS = [
    ("psychology facts", "Why your brain forgets why you walked into a room"),
    ("psychology facts", "The 2-minute rule that beats procrastination"),
    ("space facts", "What would actually happen if you fell into a black hole"),
    ("space facts", "Why we only ever see one side of the Moon"),
    ("money facts", "Why $1 today is worth more than $1 tomorrow"),
    ("money facts", "The latte factor: how small leaks sink big ships"),
    ("history facts", "The library of Alexandria: what we actually lost"),
    ("health tips", "Why you should never hit snooze (brain science)"),
    ("health tips", "What happens to your body after 30 days of walking"),
    ("tech facts", "Why your phone slows down over time"),
]


def offline_topics() -> list[dict]:
    return [{"title": t, "url": "", "channel": "evergreen", "views": 0,
             "age_days": 7.0, "duration": 45, "niche": n, "score": 1.0}
            for n, t in EVERGREEN_TOPICS]


if __name__ == "__main__":
    try:
        ranked = find_topics()
    except Exception:
        ranked = []
    if not ranked:
        print("[topics] YouTube unreachable — using evergreen topic bank.")
        ranked = offline_topics()
    for i, h in enumerate(ranked, 1):
        print(f"{i:2d}. [{h['niche']}] {h['title'][:60]}  "
              f"({h['views']:,} views / {h['age_days']}d, score {h['score']})")
