This folder stores cached preview MP3s for the voice selector.

How it works
- The UI requests `/voices/preview/{voice}` when you click Preview.
- The backend serves `app/static/voices/{voice}-preview.mp3` if present.
- If not present and `OPENAI_API_KEY` is configured, the server synthesizes a short sample via OpenAI TTS (`gpt-4o-mini-tts`), writes it here, and streams it back.
- Subsequent previews are instant because the file is served directly.

Pre-seeding previews
- To generate previews for all catalog voices in advance, run:

  `python scripts/preseed_voice_previews.py`

  This calls the same internal preview endpoint and saves the MP3s to this directory.

Notes
- Files are committed to version control so they can be served without an API key in production.
- To refresh a specific preview, delete `{voice}-preview.mp3` and run the pre-seed script (or click Preview once).

