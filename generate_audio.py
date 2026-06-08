#!/usr/bin/env python3
"""
Audio generation script for dansk-øvelse / svensk-øvelse
=========================================================
Generates MP3 files for all words and sentences in both apps.

Supports:
  --provider elevenlabs   (default, highest quality)
  --provider google       (good quality, generous free tier)

Usage:
  pip install requests
  python generate_audio.py --provider elevenlabs --key YOUR_API_KEY
  python generate_audio.py --provider google     --key YOUR_API_KEY

Output structure:
  audio/
    da/
      words/
        ikke.mp3
        måske.mp3
        ...
      sentences/
        s000.mp3
        s001.mp3
        ...
    sv/
      words/
        inte.mp3
        kanske.mp3
        ...
      sentences/
        s000.mp3
        s001.mp3
        ...

After running:
  1. Commit the audio/ folder to your GitHub repo alongside the HTML files
  2. Run: python embed_audio_map.py
     This updates the HTML files to use the audio files instead of TTS
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.request
import urllib.parse

try:
    import requests
except ImportError:
    print("Run: pip install requests")
    sys.exit(1)

# ── ElevenLabs voice IDs ──────────────────────────────────────────────────────
# These are publicly available pre-made voices.
# Danish: "Callum" works well, or use a Danish community voice.
# Swedish: "Freya" or "Charlotte" work well for Swedish.
# You can browse voices at: https://elevenlabs.io/voice-library
# and paste any voice_id you prefer below.
ELEVENLABS_VOICES = {
    "da": "onwK4e9ZLuTAKqWW03F9",   # Daniel — clear, neutral, works well for Danish
    "sv": "EXAVITQu4vr4xnSDxMaL",   # Bella — clear, works well for Swedish
}

# ── Google TTS voice names ────────────────────────────────────────────────────
GOOGLE_VOICES = {
    "da": {"languageCode": "da-DK", "name": "da-DK-Neural2-D", "ssmlGender": "MALE"},
    "sv": {"languageCode": "sv-SE", "name": "sv-SE-Neural2-A", "ssmlGender": "FEMALE"},
}


def safe_filename(text: str) -> str:
    """Convert text to a safe filename."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text, flags=re.UNICODE)
    text = re.sub(r'[\s]+', '_', text)
    text = text[:60]  # max length
    return text or hashlib.md5(text.encode()).hexdigest()[:8]


def generate_elevenlabs(text: str, lang: str, api_key: str, out_path: str):
    voice_id = ELEVENLABS_VOICES[lang]
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
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
    else:
        print(f"  ElevenLabs error {r.status_code}: {r.text[:200]}")
        return False


def generate_google(text: str, lang: str, api_key: str, out_path: str):
    url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={api_key}"
    voice = GOOGLE_VOICES[lang]
    payload = {
        "input": {"text": text},
        "voice": voice,
        "audioConfig": {
            "audioEncoding": "MP3",
            "speakingRate": 0.85,
            "pitch": 0,
        },
    }
    r = requests.post(url, json=payload, timeout=30)
    if r.status_code == 200:
        import base64
        audio_b64 = r.json()["audioContent"]
        with open(out_path, 'wb') as f:
            f.write(base64.b64decode(audio_b64))
        return True
    else:
        print(f"  Google TTS error {r.status_code}: {r.text[:200]}")
        return False


def generate_batch(items: list, lang: str, subdir: str, provider: str, api_key: str,
                   base_dir: str, is_sentence: bool = False) -> dict:
    """
    Generate audio for a list of texts.
    Returns a mapping of {text: relative_path}
    """
    out_dir = os.path.join(base_dir, "audio", lang, subdir)
    os.makedirs(out_dir, exist_ok=True)

    mapping = {}
    total = len(items)

    for i, text in enumerate(items):
        if is_sentence:
            filename = f"s{i:03d}.mp3"
        else:
            filename = safe_filename(text) + ".mp3"

        rel_path = f"audio/{lang}/{subdir}/{filename}"
        out_path = os.path.join(base_dir, rel_path)

        if os.path.exists(out_path):
            print(f"  [{i+1}/{total}] SKIP (exists): {text[:40]}")
            mapping[text] = rel_path
            continue

        print(f"  [{i+1}/{total}] Generating: {text[:50]}")

        ok = False
        for attempt in range(3):
            if attempt > 0:
                print(f"    Retry {attempt}...")
                time.sleep(2 ** attempt)
            if provider == "elevenlabs":
                ok = generate_elevenlabs(text, lang, api_key, out_path)
            else:
                ok = generate_google(text, lang, api_key, out_path)
            if ok:
                break

        if ok:
            mapping[text] = rel_path
        else:
            print(f"  FAILED: {text}")

        # Rate limiting
        if provider == "elevenlabs":
            time.sleep(0.3)   # ElevenLabs: ~3 req/sec on free tier
        else:
            time.sleep(0.05)  # Google: generous limits

    return mapping


def main():
    parser = argparse.ArgumentParser(description="Generate audio for language apps")
    parser.add_argument("--provider", choices=["elevenlabs", "google"], default="elevenlabs")
    parser.add_argument("--key", required=True, help="API key")
    parser.add_argument("--base-dir", default=".", help="Directory containing the HTML files")
    parser.add_argument("--lang", choices=["da", "sv", "both"], default="both",
                        help="Which language to generate (default: both)")
    args = parser.parse_args()

    manifest_path = os.path.join(os.path.dirname(__file__), "audio_manifest.json")
    if not os.path.exists(manifest_path):
        print(f"audio_manifest.json not found at {manifest_path}")
        print("Run this script from the directory containing your HTML files.")
        sys.exit(1)

    with open(manifest_path, encoding='utf-8') as f:
        manifest = json.load(f)

    all_mappings = {}

    if args.lang in ("da", "both"):
        print(f"\n── Danish words ({len(manifest['da_words'])}) ──────────────────")
        da_word_map = generate_batch(
            manifest["da_words"], "da", "words", args.provider, args.key, args.base_dir)

        print(f"\n── Danish sentences ({len(manifest['da_sentences'])}) ─────────")
        da_sent_map = generate_batch(
            manifest["da_sentences"], "da", "sentences", args.provider, args.key,
            args.base_dir, is_sentence=True)

        all_mappings["da_words"] = da_word_map
        all_mappings["da_sentences"] = da_sent_map

    if args.lang in ("sv", "both"):
        print(f"\n── Swedish words ({len(manifest['sv_words'])}) ──────────────────")
        sv_word_map = generate_batch(
            manifest["sv_words"], "sv", "words", args.provider, args.key, args.base_dir)

        print(f"\n── Swedish sentences ({len(manifest['sv_sentences'])}) ─────────")
        sv_sent_map = generate_batch(
            manifest["sv_sentences"], "sv", "sentences", args.provider, args.key,
            args.base_dir, is_sentence=True)

        all_mappings["sv_words"] = sv_word_map
        all_mappings["sv_sentences"] = sv_sent_map

    # Save the mappings for the embed script
    mappings_path = os.path.join(args.base_dir, "audio_mappings.json")
    with open(mappings_path, 'w', encoding='utf-8') as f:
        json.dump(all_mappings, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Done. Mappings saved to {mappings_path}")
    print("Next step: run  python embed_audio_map.py")


if __name__ == "__main__":
    main()
