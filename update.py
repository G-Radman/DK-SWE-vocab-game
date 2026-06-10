#!/usr/bin/env python3
"""
update.py — single command to update both language practice apps
================================================================
Edit words_da.json, words_sv.json, sentences_da.json, or sentences_sv.json,
then run this script. It will:

  1. Generate audio for any new entries (skipping existing files)
  2. Rebuild dansk-practice.html and svensk-practice.html from templates
  3. Inject the updated word lists and audio map into both apps

Usage:
  python update.py --elevenlabs-key YOUR_KEY

  # Rebuild HTML only (no new audio needed):
  python update.py --elevenlabs-key YOUR_KEY --no-audio

  # One language only:
  python update.py --elevenlabs-key YOUR_KEY --lang da
  python update.py --elevenlabs-key YOUR_KEY --lang sv

Then push:
  git add .
  git commit -m "Update word list"
  git push

Word list format (words_da.json / words_sv.json):
  Each entry is a JSON object with these fields:
  {
    "da":   "rolig",               <- Danish word/phrase
    "sv":   "lugn / stilla",       <- Swedish translation
    "en":   "calm, quiet",         <- English gloss (used in quiz options)
    "ipa":  "[ˈʁoˀli]",           <- pronunciation (shown after answering)
    "cat":  "Falska vänner",       <- category (used for filtering)
    "note": "⚠️ Svenska ..."       <- note shown on flashcard reveal
  }

Sentence format (sentences_da.json / sentences_sv.json):
  {
    "da":   "Jeg er egentlig ret træt i dag",
    "sv":   "Jag är egentligen ganska trött idag",
    "word": "egentlig / ret / træt"   <- focus word shown after answering
  }

Categories in use (da app):
  Falska vänner, Frekventa ord, Uttal-fällor,
  Divergent ordförråd, Verb, Fraser

Categories in use (sv app):
  Falske venner, Frekvente ord, Udtale-faldgruber,
  Divergerende ord, Verber, Fraser
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time

# ── Dependency check ──────────────────────────────────────────────────────────
missing = []
try:
    import requests
except ImportError:
    missing.append("requests")
if missing:
    print(f"Missing dependencies. Run: pip install {' '.join(missing)}")
    sys.exit(1)

# ── Config ────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ELEVENLABS_MODEL = "eleven_multilingual_v2"

# Multiple voices per language — rotated across entries for variety.
# Each word/sentence is assigned a voice deterministically based on its text,
# so the same word always gets the same voice (consistent across re-runs).
ELEVENLABS_VOICES = {
    "da": [
        "KLwMtB9otYg9CFf7AUWc",
        "a1TnjruAs5jTzdrjL8Vd",
        "54Cze5LrTSyLgbO6Fhlc",
        "rAmra0SCIYOxYmRNDSm3",
    ],
    "sv": [
        "aSLKtNoVBZlxQEMsnGL2",
        "kPdGSxhZAqy4bmPAf9iJ",
        "FCScQnyNrlLIxPiB3Bsd",
        "DSL3PSQNPbkOavwmnYl1",
    ],
}

def pick_voice(text: str, lang: str) -> str:
    """Pick a voice deterministically based on text content."""
    voices = ELEVENLABS_VOICES[lang]
    idx = int(hashlib.md5(text.encode()).hexdigest(), 16) % len(voices)
    return voices[idx]

FILES = {
    "da": {
        "words":     "words_da.json",
        "sentences": "sentences_da.json",
        "template":  "template_da.html",
        "output":    "dansk-practice.html",
    },
    "sv": {
        "words":     "words_sv.json",
        "sentences": "sentences_sv.json",
        "template":  "template_sv.html",
        "output":    "svensk-practice.html",
    },
}


# ── Helpers ───────────────────────────────────────────────────────────────────
def safe_filename(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text, flags=re.UNICODE)
    text = re.sub(r'\s+', '_', text)
    text = text[:60]
    return text or hashlib.md5(text.encode()).hexdigest()[:8]


def load_json(filename: str) -> list:
    path = os.path.join(BASE_DIR, filename)
    if not os.path.exists(path):
        print(f"ERROR: {filename} not found in {BASE_DIR}")
        sys.exit(1)
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def load_audio_map() -> dict:
    path = os.path.join(BASE_DIR, "audio_map.json")
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_audio_map(audio_map: dict):
    path = os.path.join(BASE_DIR, "audio_map.json")
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(audio_map, f, ensure_ascii=False, indent=2)


# ── Audio generation — Danish via ElevenLabs ─────────────────────────────────
def generate_elevenlabs(text: str, lang: str, api_key: str, out_path: str) -> bool:
    voice_id = pick_voice(text, lang)
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": text,
        "model_id": ELEVENLABS_MODEL,
        "voice_settings": {
            "stability": 0.6,
            "similarity_boost": 0.8,
            "style": 0.2,
            "use_speaker_boost": True,
        },
    }
    r = requests.post(url, json=payload, headers=headers, timeout=30)
    if r.status_code == 200:
        with open(out_path, 'wb') as f:
            f.write(r.content)
        return True
    print(f"  ElevenLabs error {r.status_code}: {r.text[:200]}")
    return False


def generate_da_audio(texts: list, subdir: str, audio_map: dict,
                      api_key: str, is_sentence: bool = False) -> int:
    out_dir = os.path.join(BASE_DIR, "audio", "da", subdir)
    os.makedirs(out_dir, exist_ok=True)
    new_count = 0

    for i, text in enumerate(texts):
        if text in audio_map:
            continue  # already generated

        filename = safe_filename(text) + ".mp3"
        rel_path = f"audio/da/{subdir}/{filename}"
        out_path = os.path.join(BASE_DIR, rel_path)

        if os.path.exists(out_path):
            audio_map[text] = rel_path
            continue

        print(f"  [DA] {text[:60]}")
        ok = False
        for attempt in range(3):
            if attempt > 0:
                print(f"    Retry {attempt}...")
                time.sleep(2 ** attempt)
            ok = generate_elevenlabs(text, "da", api_key, out_path)
            if ok:
                break

        if ok:
            audio_map[text] = rel_path
            new_count += 1
        else:
            print(f"  FAILED: {text}")

        time.sleep(0.35)

    return new_count


# ── Audio generation — Swedish via edge-tts ───────────────────────────────────
def generate_sv_audio(texts: list, subdir: str, audio_map: dict,
                      api_key: str, is_sentence: bool = False) -> int:
    out_dir = os.path.join(BASE_DIR, "audio", "sv", subdir)
    os.makedirs(out_dir, exist_ok=True)
    new_count = 0

    for i, text in enumerate(texts):
        if text in audio_map:
            continue

        filename = safe_filename(text) + ".mp3"
        rel_path = f"audio/sv/{subdir}/{filename}"
        out_path = os.path.join(BASE_DIR, rel_path)

        if os.path.exists(out_path):
            audio_map[text] = rel_path
            continue

        print(f"  [SV] {text[:60]}")
        ok = False
        for attempt in range(3):
            if attempt > 0:
                print(f"    Retry {attempt}...")
                time.sleep(2 ** attempt)
            ok = generate_elevenlabs(text, "sv", api_key, out_path)
            if ok:
                break

        if ok:
            audio_map[text] = rel_path
            new_count += 1
        else:
            print(f"  FAILED: {text}")

        time.sleep(0.35)

    return new_count


# ── HTML building ─────────────────────────────────────────────────────────────
def esc(s: str) -> str:
    """Escape a string for embedding in a JS double-quoted string."""
    return s.replace('\\', '\\\\').replace('"', '\\"')


def words_to_js(words: list) -> str:
    lines = ['const WORDS=[']
    for w in words:
        lines.append(
            f'  {{da:"{esc(w["da"])}",sv:"{esc(w["sv"])}",en:"{esc(w["en"])}",'
            f'ipa:"{esc(w["ipa"])}",cat:"{esc(w["cat"])}",note:"{esc(w["note"])}"}}, '
        )
    lines.append('];')
    return '\n'.join(lines)


def sentences_to_js(sentences: list) -> str:
    return 'const SENTENCES=' + json.dumps(sentences, ensure_ascii=False) + ';'


def audio_map_to_js(audio_map: dict) -> str:
    """Build the JS speak() function that uses pre-generated audio."""
    entries = ',\n'.join(
        f'  {json.dumps(k, ensure_ascii=False)}: {json.dumps(v, ensure_ascii=False)}'
        for k, v in audio_map.items()
    )
    return f"""// ─── AUDIO MAP ─────────────────────────────────────────────────
const AUDIO_MAP = {{
{entries}
}};

let _currentAudio = null;

function playAudio(path, btnId, fallbackText, fallbackLang) {{
  if (_currentAudio) {{ _currentAudio.pause(); _currentAudio = null; }}
  document.querySelectorAll('.speaking').forEach(b => b.classList.remove('speaking'));
  const btn = btnId ? document.getElementById(btnId) : null;
  if (btn) btn.classList.add('speaking');
  const audio = new Audio(path);
  _currentAudio = audio;
  audio.playbackRate = 0.92;
  const cleanup = () => {{
    if (btn) btn.classList.remove('speaking');
    if (_currentAudio === audio) _currentAudio = null;
  }};
  audio.addEventListener('ended', cleanup);
  audio.addEventListener('error', () => {{ cleanup(); speakTTS(fallbackText, fallbackLang, btnId); }});
  audio.play().catch(() => {{ cleanup(); speakTTS(fallbackText, fallbackLang, btnId); }});
}}

function speakTTS(text, lang, btnId) {{
  if (!window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  const utt = new SpeechSynthesisUtterance(text);
  utt.lang = lang; utt.rate = 0.82;
  const voices = window.speechSynthesis.getVoices();
  const v = voices.find(x => x.lang.startsWith(lang.slice(0, 2)));
  if (v) utt.voice = v;
  if (btnId) {{
    const btn = document.getElementById(btnId);
    if (btn) btn.classList.add('speaking');
    utt.onend = utt.onerror = () => {{
      const b = document.getElementById(btnId);
      if (b) b.classList.remove('speaking');
    }};
  }}
  window.speechSynthesis.speak(utt);
}}

function speak(text, lang, btnId) {{
  const path = AUDIO_MAP[text];
  if (path) {{ playAudio(path, btnId, text, lang); }}
  else {{ speakTTS(text, lang, btnId); }}
}}

"""


def build_html(lang: str, sentences: list, audio_map: dict):
    cfg = FILES[lang]
    template_path = os.path.join(BASE_DIR, cfg["template"])
    output_path = os.path.join(BASE_DIR, cfg["output"])

    if not os.path.exists(template_path):
        print(f"ERROR: template {cfg['template']} not found.")
        print("Make sure template_da.html and template_sv.html are in the same folder.")
        sys.exit(1)

    with open(template_path, encoding='utf-8') as f:
        template = f.read()

    # Replace the speak() function section with audio map version
    speech_start = template.find('// ─── SPEECH ─')
    tabs_start = template.find('// ─── TABS ─')
    if speech_start != -1 and tabs_start != -1:
        template = (
            template[:speech_start] +
            audio_map_to_js(audio_map) +
            template[tabs_start:]
        )
    # If already replaced (template already has AUDIO_MAP), update it
    elif '// ─── AUDIO MAP ─' in template:
        am_start = template.find('// ─── AUDIO MAP ─')
        # Find end of speak() function — look for next major section marker
        am_end = template.find('\n// ─── TABS ─', am_start)
        if am_end == -1:
            am_end = template.find('\n// ─── STATE ─', am_start)
        if am_end != -1:
            template = template[:am_start] + audio_map_to_js(audio_map) + template[am_end+1:]

    # Inject SENTENCES
    html = template.replace('/*SENTENCES_PLACEHOLDER*/', sentences_to_js(sentences))

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"  ✓ {cfg['output']} rebuilt ({len(sentences)} sentences)")


# ── Main ──────────────────────────────────────────────────────────────────────
def run(lang: str, api_key: str, no_audio: bool):
    audio_map = load_audio_map()
    total_new = 0

    langs = ["da", "sv"] if lang == "both" else [lang]

    for lg in langs:
        cfg = FILES[lg]
        words = load_json(cfg["words"])
        sentences = load_json(cfg["sentences"])

        spoken_field = "da" if lg == "da" else "sv"
        word_texts = [w[spoken_field] for w in words]
        sent_texts = [s[spoken_field] for s in sentences]

        if not no_audio:
            print(f"\n── {lg.upper()} audio ────────────────────────────────────────")
            if lg == "da":
                new = generate_da_audio(word_texts, "words", audio_map, api_key)
                new += generate_da_audio(sent_texts, "sentences", audio_map, api_key, is_sentence=True)
            else:
                new = generate_sv_audio(word_texts, "words", audio_map, api_key)
                new += generate_sv_audio(sent_texts, "sentences", audio_map, api_key, is_sentence=True)

            total_new += new
            if new:
                print(f"  {new} new files generated")
            else:
                print(f"  All up to date")

        save_audio_map(audio_map)

        print(f"\n── Building {cfg['output']} ─────────────────────────────────")
        build_html(lg, sentences, audio_map)

    print(f"\n✓ Done. {total_new} new audio files generated.")
    print("\nPush to GitHub:")
    print("  git add .")
    print("  git commit -m \"Update word list\"")
    print("  git push")


def main():
    parser = argparse.ArgumentParser(
        description="Update language practice apps — generates audio and rebuilds HTML"
    )
    parser.add_argument("--elevenlabs-key", required=True, help="ElevenLabs API key")
    parser.add_argument("--lang", choices=["da", "sv", "both"], default="both")
    parser.add_argument("--no-audio", action="store_true",
                        help="Skip audio generation, just rebuild HTML")
    args = parser.parse_args()

    run(args.lang, args.elevenlabs_key, args.no_audio)


if __name__ == "__main__":
    main()
