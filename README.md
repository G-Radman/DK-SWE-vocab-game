# Language Practice Apps

## Files in this repo

| File | Description |
|---|---|
| `dansk-practice.html` | Swedish speaker learning Danish ← **generated, don't edit** |
| `svensk-practice.html` | Danish speaker learning Swedish ← **generated, don't edit** |
| `template_da.html` | HTML template for the Danish app |
| `template_sv.html` | HTML template for the Swedish app |
| `words_da.json` | ✏️ Word list for the Danish app — **edit this** |
| `words_sv.json` | ✏️ Word list for the Swedish app — **edit this** |
| `sentences_da.json` | ✏️ Sentence list for the Danish app — **edit this** |
| `sentences_sv.json` | ✏️ Sentence list for the Swedish app — **edit this** |
| `audio_map.json` | Generated — maps text to audio file paths |
| `update.py` | Single script: generates audio + rebuilds HTML |

---

## Setup (first time only)

```powershell
pip install requests edge-tts
```

---

## Updating the word or sentence lists

### 1. Edit the JSON file

Open `words_da.json`, `words_sv.json`, `sentences_da.json`, or `sentences_sv.json`
and add, remove, or edit entries.

**Word entry format:**
```json
{
  "da":   "rolig",
  "sv":   "lugn / stilla",
  "en":   "calm, quiet",
  "ipa":  "[ˈʁoˀli]",
  "cat":  "Falska vänner",
  "note": "⚠️ Svenska <strong>'rolig'</strong> = kul. Danska 'rolig' = lugn."
}
```

**Sentence entry format:**
```json
{
  "da":   "Jeg er egentlig ret træt i dag",
  "sv":   "Jag är egentligen ganska trött idag",
  "word": "egentlig / ret / træt"
}
```

Categories in use:
- Danish app: `Falska vänner`, `Frekventa ord`, `Uttal-fällor`, `Divergent ordförråd`, `Verb`, `Fraser`
- Swedish app: `Falske venner`, `Frekvente ord`, `Udtale-faldgruber`, `Divergerende ord`, `Verber`, `Fraser`

### 2. Run update.py

```powershell
python update.py --elevenlabs-key YOUR_KEY
```

This will:
- Generate audio for any new entries (skipping existing files)
- Rebuild both HTML files with the updated content

One language only:
```powershell
python update.py --elevenlabs-key YOUR_KEY --lang da
python update.py --elevenlabs-key YOUR_KEY --lang sv
```

Rebuild HTML without generating new audio (e.g. after fixing a typo):
```powershell
python update.py --elevenlabs-key YOUR_KEY --no-audio
```

### 3. Push to GitHub

```powershell
git add .
git commit -m "Add new words"
git push
```

---

## Audio providers

| Language | Provider | Voice |
|---|---|---|
| Danish | ElevenLabs free tier | Daniel (`onwK4e9ZLuTAKqWW03F9`) |
| Swedish | edge-tts (free, no account) | MattiasNeural |

To change a voice, update `ELEVENLABS_VOICE_ID` or `EDGE_VOICE` at the top
of `update.py`, delete the relevant `audio/da/` or `audio/sv/` folder,
and re-run `update.py`.

---

## Notes

- The `audio/` folder will be roughly **15–25 MB** total
- ElevenLabs free tier: 10,000 characters/month (~4,500 chars for all Danish audio)
- Already-generated audio files are never regenerated — only new entries cost credits
- The HTML files are fully rebuilt each time, so it's always in sync with the JSON
