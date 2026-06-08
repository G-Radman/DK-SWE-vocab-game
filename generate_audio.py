#!/usr/bin/env python3
"""
Audio generation script for dansk-practice / svensk-practice
=============================================================
Uses two providers:
  - Danish:  ElevenLabs (Daniel voice) — best quality for Danish
  - Swedish: edge-tts (MattiasNeural)  — native Swedish, free

Setup:
  pip install requests edge-tts

Usage:
  python generate_audio.py --elevenlabs-key YOUR_KEY

  # Regenerate only one language:
  python generate_audio.py --elevenlabs-key YOUR_KEY --lang da
  python generate_audio.py --elevenlabs-key YOUR_KEY --lang sv

After running:
  python embed_audio_map.py
  git add audio/ dansk-practice.html svensk-practice.html
  git commit -m "Add pre-generated audio"
  git push
"""

import argparse
import asyncio
import hashlib
import json
import os
import re
import sys
import time

missing = []
try:
    import requests
except ImportError:
    missing.append("requests")
try:
    import edge_tts
except ImportError:
    missing.append("edge-tts")
if missing:
    print(f"Run: pip install {' '.join(missing)}")
    sys.exit(1)

# ── ElevenLabs — Danish ───────────────────────────────────────────────────────
ELEVENLABS_VOICE_ID = "onwK4e9ZLuTAKqWW03F9"  # Daniel
ELEVENLABS_MODEL    = "eleven_multilingual_v2"

# ── edge-tts — Swedish ────────────────────────────────────────────────────────
EDGE_VOICE = "sv-SE-MattiasNeural"
EDGE_RATE  = "-10%"  # slightly slower for learning


def safe_filename(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text, flags=re.UNICODE)
    text = re.sub(r'\s+', '_', text)
    text = text[:60]
    return text or hashlib.md5(text.encode()).hexdigest()[:8]


# ── Danish via ElevenLabs ─────────────────────────────────────────────────────
def generate_elevenlabs(text: str, api_key: str, out_path: str) -> bool:
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
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
    else:
        print(f"  ElevenLabs error {r.status_code}: {r.text[:200]}")
        return False


def generate_da_batch(items: list, api_key: str, subdir: str,
                      base_dir: str, is_sentence: bool = False) -> dict:
    out_dir = os.path.join(base_dir, "audio", "da", subdir)
    os.makedirs(out_dir, exist_ok=True)
    mapping = {}
    total = len(items)

    for i, text in enumerate(items):
        filename = f"s{i:03d}.mp3" if is_sentence else safe_filename(text) + ".mp3"
        rel_path = f"audio/da/{subdir}/{filename}"
        out_path = os.path.join(base_dir, rel_path)

        if os.path.exists(out_path):
            print(f"  [{i+1}/{total}] SKIP: {text[:50]}")
            mapping[text] = rel_path
            continue

        print(f"  [{i+1}/{total}] {text[:60]}")

        ok = False
        for attempt in range(3):
            if attempt > 0:
                print(f"    Retry {attempt}...")
                time.sleep(2 ** attempt)
            ok = generate_elevenlabs(text, api_key, out_path)
            if ok:
                break

        if ok:
            mapping[text] = rel_path
        else:
            print(f"  FAILED: {text}")

        time.sleep(0.35)  # ElevenLabs free tier: ~3 req/sec

    return mapping


# ── Swedish via edge-tts ──────────────────────────────────────────────────────
async def generate_edge(text: str, out_path: str) -> bool:
    try:
        communicate = edge_tts.Communicate(text, EDGE_VOICE, rate=EDGE_RATE)
        await communicate.save(out_path)
        return True
    except Exception as e:
        print(f"  edge-tts error: {e}")
        return False


async def generate_sv_batch(items: list, subdir: str,
                            base_dir: str, is_sentence: bool = False) -> dict:
    out_dir = os.path.join(base_dir, "audio", "sv", subdir)
    os.makedirs(out_dir, exist_ok=True)
    mapping = {}
    total = len(items)

    for i, text in enumerate(items):
        filename = f"s{i:03d}.mp3" if is_sentence else safe_filename(text) + ".mp3"
        rel_path = f"audio/sv/{subdir}/{filename}"
        out_path = os.path.join(base_dir, rel_path)

        if os.path.exists(out_path):
            print(f"  [{i+1}/{total}] SKIP: {text[:50]}")
            mapping[text] = rel_path
            continue

        print(f"  [{i+1}/{total}] {text[:60]}")

        ok = False
        for attempt in range(3):
            if attempt > 0:
                print(f"    Retry {attempt}...")
                await asyncio.sleep(2 ** attempt)
            ok = await generate_edge(text, out_path)
            if ok:
                break

        if ok:
            mapping[text] = rel_path
        else:
            print(f"  FAILED: {text}")

    return mapping


# ── Main ──────────────────────────────────────────────────────────────────────
async def main_async(lang: str, base_dir: str, elevenlabs_key: str):
    manifest_path = os.path.join(base_dir, "audio_manifest.json")
    if not os.path.exists(manifest_path):
        print(f"audio_manifest.json not found in {base_dir}")
        print("Make sure you're running from the folder containing the HTML files.")
        sys.exit(1)

    with open(manifest_path, encoding='utf-8') as f:
        manifest = json.load(f)

    mappings_path = os.path.join(base_dir, "audio_mappings.json")
    if os.path.exists(mappings_path):
        with open(mappings_path, encoding='utf-8') as f:
            all_mappings = json.load(f)
    else:
        all_mappings = {}

    if lang in ("da", "both"):
        print(f"\n── Danish words ({len(manifest['da_words'])}) — ElevenLabs/Daniel ──")
        all_mappings["da_words"] = generate_da_batch(
            manifest["da_words"], elevenlabs_key, "words", base_dir)

        print(f"\n── Danish sentences ({len(manifest['da_sentences'])}) — ElevenLabs/Daniel ──")
        all_mappings["da_sentences"] = generate_da_batch(
            manifest["da_sentences"], elevenlabs_key, "sentences", base_dir, is_sentence=True)

    if lang in ("sv", "both"):
        print(f"\n── Swedish words ({len(manifest['sv_words'])}) — edge-tts/Mattias ──")
        all_mappings["sv_words"] = await generate_sv_batch(
            manifest["sv_words"], "words", base_dir)

        print(f"\n── Swedish sentences ({len(manifest['sv_sentences'])}) — edge-tts/Mattias ──")
        all_mappings["sv_sentences"] = await generate_sv_batch(
            manifest["sv_sentences"], "sentences", base_dir, is_sentence=True)

    with open(mappings_path, 'w', encoding='utf-8') as f:
        json.dump(all_mappings, f, ensure_ascii=False, indent=2)

    total_ok = sum(len(v) for v in all_mappings.values())
    print(f"\n✓ Done — {total_ok} audio files ready.")
    print(f"\nNext step: python embed_audio_map.py")


def main():
    parser = argparse.ArgumentParser(description="Generate audio for language practice apps")
    parser.add_argument("--elevenlabs-key", required=True, help="ElevenLabs API key")
    parser.add_argument("--lang", choices=["da", "sv", "both"], default="both",
                        help="Which language to generate (default: both)")
    parser.add_argument("--base-dir", default=".",
                        help="Directory containing the HTML files (default: current folder)")
    args = parser.parse_args()

    asyncio.run(main_async(args.lang, args.base_dir, args.elevenlabs_key))


if __name__ == "__main__":
    main()
