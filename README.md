# Language Apps — Audio Setup

## Files in this repo

| File | Description |
|---|---|
| `dansk-practice.html` | Swedish speaker learning Danish |
| `svensk-practice.html` | Danish speaker learning Swedish |
| `generate_audio.py` | Generates MP3 files |
| `embed_audio_map.py` | Patches the HTML files to use the generated audio |
| `audio_manifest.json` | List of all strings that need audio |

---

## Audio providers

| Language | Provider | Voice |
|---|---|---|
| Danish | ElevenLabs (free tier) | Daniel — `onwK4e9ZLuTAKqWW03F9` |
| Swedish | edge-tts (free, no account) | MattiasNeural |

---

## Step 1 — Install dependencies

```powershell
pip install requests edge-tts
```

---

## Step 2 — Get your ElevenLabs API key

1. Sign up / log in at https://elevenlabs.io
2. Go to your profile → API Key
3. Copy the key

---

## Step 3 — Generate the audio

Run from the folder containing the HTML files:

```powershell
python generate_audio.py --elevenlabs-key YOUR_KEY
```

Regenerate only one language:

```powershell
python generate_audio.py --elevenlabs-key YOUR_KEY --lang da
python generate_audio.py --elevenlabs-key YOUR_KEY --lang sv
```

Already-generated files are skipped, so it's safe to interrupt and resume.

---

## Step 4 — Patch the HTML files

```powershell
python embed_audio_map.py
```

Updates both HTML files to play the MP3s instead of browser TTS.
Originals are backed up as `*.original.html`.

---

## Step 5 — Push to GitHub

```powershell
git add audio/ dansk-practice.html svensk-practice.html
git commit -m "Add pre-generated audio"
git push
```

---

## Changing a voice

Edit `ELEVENLABS_VOICE_ID` or `EDGE_VOICE` at the top of `generate_audio.py`,
delete the relevant `audio/da/` or `audio/sv/` folder, then re-run:

```powershell
python generate_audio.py --elevenlabs-key YOUR_KEY --lang da   # or --lang sv
python embed_audio_map.py
git add audio/ dansk-practice.html svensk-practice.html
git commit -m "Update voice"
git push
```

Other ElevenLabs built-in voices (all free, all work well for Danish):
- Daniel: `onwK4e9ZLuTAKqWW03F9` (default)
- Callum: `N2lVS1w4EtoT3dr4eOWO`
- Adam:   `pNInz6obpgDQGcFmaJgB`

Other edge-tts Swedish voices:
- `sv-SE-MattiasNeural` (male, default)
- `sv-SE-SofieNeural`   (female)

---

## Notes

- The `audio/` folder will be roughly **15–25 MB** total (744 MP3 files)
- ElevenLabs free tier gives 10,000 characters/month — enough to generate
  all Danish audio once (≈4,500 chars) with room to spare
- If you add new words later, re-run `generate_audio.py` (skips existing
  files), then `embed_audio_map.py`, then push
