# ShortsAgent — mobile-friendly online Shorts maker

This is a Streamlit web version of the ShortsAgent ZIP you supplied. It creates a 720p vertical MP4 with a generated script, neural voiceover, and timed captions.

## Deploy free from your phone

1. Download and extract this ZIP on your phone.
2. Create/sign in to a GitHub account at https://github.com.
3. Create a **public** repository, for example `shortsagent-web`.
4. In the repository, choose **Add file → Upload files** and upload the contents of this extracted folder. Upload all the files shown in this ZIP into the repository root. There are no nested folders you need to create.
5. Open https://share.streamlit.io and sign in with GitHub.
6. Tap **Create app**, select your `shortsagent-web` repository, branch `main`, and main file path `app.py`. Deploy.
7. Once the app starts, open its Streamlit URL on your phone.
8. Get a Gemini API key at https://aistudio.google.com/app/apikey and paste it into the app. Pexels is optional.

## Cost and limits

- Streamlit Community Cloud offers free app hosting for personal, educational, and non-commercial use. Check its current terms and resource limits before relying on it for commercial use.
- A free app may have resource limits or temporary availability constraints. Rendering 720p video can take several minutes and may fail for long or complex jobs.
- Gemini API free-tier access and quotas can change. The app uses `gemini-3.6-flash`; if Google changes model availability, update `script_writer.LLM_MODEL` in `app.py` to a currently available model.
- Edge TTS is accessed online and depends on service availability.
- Pexels API key is optional; without it the video uses the built-in animated gradient background.
- Generated videos are stored temporarily on the hosting machine. Download your MP4 as soon as it is ready.
- This version exports MP4s; it does not upload automatically to YouTube.

## Security

Do not put API keys in GitHub files. Paste your Gemini/Pexels keys only into the app's password fields. The app does not write the entered keys to disk.
