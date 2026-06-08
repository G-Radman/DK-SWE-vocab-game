# Language Apps — Audio Setup

## Files in this repo

| File | Description |
|---|---|
| `dansk-øvelse.html` | Swedish speaker learning Danish |
| `svensk-øvelse.html` | Danish speaker learning Swedish |
| `generate_audio.py` | Generates MP3 files via ElevenLabs or Google TTS |
| `embed_audio_map.py` | Patches the HTML files to use the generated audio |
| `audio_manifest.json` | List of all strings that need audio (auto-generated) |

---

## Step 1 — Get an API key

**Option A: ElevenLabs** (recommended — best quality)
1. Sign up at https://elevenlabs.io
2. Free tier gives 10,000 characters/month — enough to generate all audio once
3. Find your API key at https://elevenlabs.io/profile → API Key
4. The script uses `eleven_multilingual_v2` which handles both Danish and Swedish naturally

**Option B: Google Cloud TTS** (also excellent)
1. Go to https://console.cloud.google.com
2. Enable the "Cloud Text-to-Speech API"
3. Create an API key under APIs & Services → Credentials
4. Free tier: 1 million characters/month for WaveNet voices

---

## Step 2 — Generate the audio

Make sure you have Python 3 and the `requests` library:

```bash
pip install requests
```

Run the generation script from the folder containing the HTML files:

```bash
# ElevenLabs
python generate_audio.py --provider elevenlabs --key YOUR_API_KEY

# Google TTS
python generate_audio.py --provider google --key YOUR_API_KEY

# Generate only one language
python generate_audio.py --provider elevenlabs --key YOUR_KEY --lang da
python generate_audio.py --provider elevenlabs --key YOUR_KEY --lang sv
```

This creates an `audio/` folder:
```
audio/
  da/
    words/      ← one MP3 per Danish word
    sentences/  ← one MP3 per Danish sentence
  sv/
    words/      ← one MP3 per Swedish word
    sentences/  ← one MP3 per Swedish sentence
```

It's safe to run multiple times — already-generated files are skipped.

---

## Step 3 — Patch the HTML files

```bash
python embed_audio_map.py
```

This updates `dansk-øvelse.html` and `svensk-øvelse.html` to play the MP3 files
instead of using the browser's built-in TTS. Original files are backed up as
`*.original.html`.

The patched apps fall back to browser TTS automatically if an audio file fails
to load for any reason.

---

## Step 4 — Push to GitHub

```bash
git add audio/ dansk-øvelse.html svensk-øvelse.html
git commit -m "Add pre-generated audio"
git push
```

GitHub Pages will serve the MP3 files directly. The apps work on any browser
on any device, online or offline (once cached).

---

## Changing voice

**ElevenLabs:** Browse voices at https://elevenlabs.io/voice-library
Find a voice you like, copy its ID from the URL, and update `ELEVENLABS_VOICES`
in `generate_audio.py`:

```python
ELEVENLABS_VOICES = {
    "da": "PASTE_DANISH_VOICE_ID_HERE",
    "sv": "PASTE_SWEDISH_VOICE_ID_HERE",
}
```

Then delete the `audio/` folder and run `generate_audio.py` again.

**Google:** Update `GOOGLE_VOICES` in `generate_audio.py`. Available voices:
- Danish: `da-DK-Neural2-D` (male), `da-DK-Neural2-F` (female)  
- Swedish: `sv-SE-Neural2-A` (female), `sv-SE-Neural2-B` (male)

---

## Notes

- The `audio/` folder will be roughly **15–25 MB** total (744 MP3 files)
- GitHub Pages has a soft limit of 1 GB per repo — well within range
- If you add new words to the app later, re-run `generate_audio.py`
  (it skips existing files) then `embed_audio_map.py` again
