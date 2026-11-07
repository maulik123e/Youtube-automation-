"""Mobile-friendly Streamlit web app for ShortsAgent."""
from pathlib import Path
import re
import streamlit as st

import config
import script_writer
import voice
import video
import topics as topic_finder

ROOT = Path(__file__).parent

# 720p/24fps keeps rendering more practical on a free CPU server.
video.VIDEO_W = 720
video.VIDEO_H = 1280
video.FPS = 24
video.CAPTION_FONT_SIZE = 52

VOICES = {
    "Andrew — US male": "en-US-AndrewNeural",
    "Jenny — US female": "en-US-JennyNeural",
    "Guy — US male": "en-US-GuyNeural",
    "Aria — US female": "en-US-AriaNeural",
    "Ryan — UK male": "en-GB-RyanNeural",
    "Sonia — UK female": "en-GB-SoniaNeural",
}

st.set_page_config(page_title="ShortsAgent | AI Shorts Maker", page_icon="🎬", layout="centered")
st.title("🎬 ShortsAgent")
st.subheader("Turn an idea into a captioned YouTube Short — from your phone.")
st.caption("AI script · Neural voiceover · Word-timed captions · Vertical MP4")

with st.expander("🔑 Free API settings", expanded=True):
    gemini_key = st.text_input("Gemini API key", type="password", help="Get a free key from Google AI Studio. It is used only while generating and is not saved to a file.")
    pexels_key = st.text_input("Pexels API key (optional)", type="password", help="Without this, the video uses the built-in animated gradient background.")

create_tab, ideas_tab = st.tabs(["✨ Create a Short", "🔥 Find topic ideas"])
with create_tab:
    topic = st.text_area("Video topic", placeholder="Why your brain forgets why you walked into a room", height=90)
    niche = st.text_input("Niche", value="psychology facts")
    c1, c2 = st.columns(2)
    with c1:
        voice_label = st.selectbox("Voice", list(VOICES.keys()))
    with c2:
        rate = st.selectbox("Speaking speed", ["-5%", "+0%", "+5%", "+8%", "+12%"], index=3)

    if st.button("🚀 Generate my Short", type="primary", use_container_width=True):
        if len(topic.strip()) < 4:
            st.error("Enter a topic with at least 4 characters.")
        elif not gemini_key.strip():
            st.error("A Gemini API key is required for AI scripts. Get one free at https://aistudio.google.com/app/apikey")
        else:
            try:
                config.ensure_dirs()
                script_writer.LLM_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
                script_writer.LLM_API_KEY = gemini_key.strip()
                script_writer.LLM_MODEL = "gemini-3.6-flash"
                voice.TTS_VOICE = VOICES[voice_label]
                voice.TTS_RATE = rate
                video.PEXELS_API_KEY = pexels_key.strip()
                slug = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")[:40] or "short"
                bar = st.progress(5, text="Writing your script with Gemini…")
                script = script_writer.write_script(topic.strip(), niche.strip() or "general")
                script_path = script_writer.save_script(script, slug)
                bar.progress(30, text="Generating neural voiceover…")
                mp3, words = voice.synthesize(script_writer.spoken_text(script), slug)
                bar.progress(50, text="Building vertical video and animated captions…")
                output = video.build_video(mp3, script, words, slug, bg_query=topic.strip())
                bar.progress(100, text="Your Short is ready!")
                st.success("Video created successfully.")
                st.video(output)
                with open(output, "rb") as f:
                    st.download_button("⬇️ Download MP4", data=f.read(), file_name=Path(output).name, mime="video/mp4", use_container_width=True)
                st.markdown("### Generated script")
                st.markdown("**" + script.get("title", topic) + "**")
                st.write("\n".join(script.get("lines", [])))
                st.caption(script.get("description", ""))
                with open(script_path, "rb") as f:
                    st.download_button("Download script JSON", data=f.read(), file_name=Path(script_path).name, mime="application/json")
            except Exception as exc:
                st.error(f"Generation failed: {exc}")
                st.info("If this persists, check the app logs and confirm that the API key and free-tier quota are valid.")

with ideas_tab:
    niches = st.text_input("Niches (comma-separated)", value="psychology facts, space facts, money facts")
    if st.button("Find trending ideas", use_container_width=True):
        selected = [x.strip() for x in niches.split(",") if x.strip()]
        with st.spinner("Searching recent YouTube videos for topic ideas…"):
            try:
                hits = topic_finder.find_topics(selected, per_niche=3)
                if not hits:
                    st.info("No ideas found. Try again later.")
                for hit in hits[:12]:
                    st.markdown(f"**{hit['title']}**  \n{hit['niche']} · {hit['views']:,} views · {hit['age_days']} days old")
            except Exception as exc:
                st.error(f"Topic search failed: {exc}")

st.divider()
st.caption("Free hosting may sleep when idle and has resource limits. Rendering can take several minutes. Review each video before publishing. API keys are not written to project files. This version creates MP4 files; automatic YouTube uploading is not included yet.")
