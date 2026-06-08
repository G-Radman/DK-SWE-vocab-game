#!/usr/bin/env python3
"""
embed_audio_map.py
==================
Patches dansk-øvelse.html and svensk-øvelse.html to use
pre-generated audio files instead of the Web Speech API.

Run this AFTER generate_audio.py has finished.

Usage:
    python embed_audio_map.py
"""

import json
import os
import re
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MAPPINGS_PATH = os.path.join(BASE_DIR, "audio_mappings.json")
DA_HTML = os.path.join(BASE_DIR, "dansk-practice.html")
SV_HTML = os.path.join(BASE_DIR, "svensk-practice.html")

# The JS we'll inject into both files — replaces the speak() function
# with one that plays a pre-generated MP3, falling back to TTS if not found.
AUDIO_JS_TEMPLATE = """
// ── Pre-generated audio maps ──────────────────────────────────────────────
const WORD_AUDIO = {word_map};
const SENT_AUDIO = {sent_map};

// ── Audio player (uses pre-generated MP3 with TTS fallback) ──────────────
let _currentAudio = null;

function playAudio(path, btnId, fallbackText, fallbackLang) {
  if (_currentAudio) {
    _currentAudio.pause();
    _currentAudio = null;
  }
  // Clear any speaking state
  document.querySelectorAll('.speaking').forEach(b => b.classList.remove('speaking'));

  const btn = btnId ? document.getElementById(btnId) : null;
  if (btn) btn.classList.add('speaking');

  const audio = new Audio(path);
  _currentAudio = audio;
  audio.playbackRate = 0.92;

  const cleanup = () => {
    if (btn) btn.classList.remove('speaking');
    if (_currentAudio === audio) _currentAudio = null;
  };

  audio.addEventListener('ended', cleanup);
  audio.addEventListener('error', () => {
    cleanup();
    // Fallback to TTS if file fails to load
    speakTTS(fallbackText, fallbackLang, btnId);
  });

  audio.play().catch(() => {
    cleanup();
    speakTTS(fallbackText, fallbackLang, btnId);
  });
}

function speakTTS(text, lang, btnId) {
  if (!window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  const utt = new SpeechSynthesisUtterance(text);
  utt.lang = lang; utt.rate = 0.82;
  const voices = window.speechSynthesis.getVoices();
  const v = voices.find(x => x.lang.startsWith(lang.slice(0, 2)));
  if (v) utt.voice = v;
  if (btnId) {
    const btn = document.getElementById(btnId);
    if (btn) btn.classList.add('speaking');
    utt.onend = utt.onerror = () => {
      const b = document.getElementById(btnId);
      if (b) b.classList.remove('speaking');
    };
  }
  window.speechSynthesis.speak(utt);
}

function speak(text, lang, btnId) {
  const path = WORD_AUDIO[text] || SENT_AUDIO[text];
  if (path) {
    playAudio(path, btnId, text, lang);
  } else {
    speakTTS(text, lang, btnId);
  }
}
"""

def make_js_map(mapping: dict) -> str:
    """Convert a Python dict to a JS object literal."""
    parts = []
    for text, path in mapping.items():
        k = json.dumps(text, ensure_ascii=False)
        v = json.dumps(path, ensure_ascii=False)
        parts.append(f"  {k}: {v}")
    return "{\n" + ",\n".join(parts) + "\n}"


def patch_html(html_path: str, word_map: dict, sent_map: dict, lang_label: str):
    print(f"\nPatching {os.path.basename(html_path)}...")

    with open(html_path, encoding='utf-8') as f:
        content = f.read()

    # Back up original
    backup = html_path.replace('.html', '.original.html')
    if not os.path.exists(backup):
        shutil.copy(html_path, backup)
        print(f"  Backed up to {os.path.basename(backup)}")

    # Build the audio JS block
    word_js = make_js_map(word_map)
    sent_js = make_js_map(sent_map)
    audio_js = AUDIO_JS_TEMPLATE.replace('{word_map}', word_js).replace('{sent_map}', sent_js)

    # Replace the speak() function + everything from SPEECH comment to TABS comment
    # Find the speech section
    speech_start = content.find('// ─── SPEECH ─')
    speech_end = content.find('// ─── TABS ─')

    if speech_start == -1 or speech_end == -1:
        print("  ERROR: Could not find SPEECH section markers")
        return False

    content = content[:speech_start] + audio_js + '\n' + content[speech_end:]

    # Remove initVoices() call from window.onload since we don't need it
    content = content.replace('  initVoices();\n', '')

    # Remove the initVoices function itself
    iv_start = content.find('function initVoices()')
    if iv_start != -1:
        # Find the closing brace
        depth = 0
        i = content.find('{', iv_start)
        while i < len(content):
            if content[i] == '{':
                depth += 1
            elif content[i] == '}':
                depth -= 1
                if depth == 0:
                    content = content[:iv_start] + content[i+1:]
                    break
            i += 1

    # Remove getBestDanishVoice and showVoiceBanner functions (no longer needed)
    for fn_name in ['getBestDanishVoice', 'showVoiceBanner']:
        fn_start = content.find(f'function {fn_name}(')
        if fn_start != -1:
            depth = 0
            i = content.find('{', fn_start)
            while i < len(content):
                if content[i] == '{':
                    depth += 1
                elif content[i] == '}':
                    depth -= 1
                    if depth == 0:
                        content = content[:fn_start] + content[i+1:]
                        break
                i += 1

    # Remove the _daVoice and _voiceWarningShown variable declarations
    content = re.sub(r'let _daVoice = null;\s*\n', '', content)
    content = re.sub(r'let _voiceWarningShown = false;\s*\n', '', content)

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"  ✓ Patched. Word audio entries: {len(word_map)}, sentence: {len(sent_map)}")
    return True


def main():
    if not os.path.exists(MAPPINGS_PATH):
        print(f"audio_mappings.json not found.")
        print("Run generate_audio.py first.")
        return

    with open(MAPPINGS_PATH, encoding='utf-8') as f:
        mappings = json.load(f)

    da_word_map = mappings.get("da_words", {})
    da_sent_map = mappings.get("da_sentences", {})
    sv_word_map = mappings.get("sv_words", {})
    sv_sent_map = mappings.get("sv_sentences", {})

    print(f"Loaded mappings:")
    print(f"  DA: {len(da_word_map)} words, {len(da_sent_map)} sentences")
    print(f"  SV: {len(sv_word_map)} words, {len(sv_sent_map)} sentences")

    if os.path.exists(DA_HTML):
        patch_html(DA_HTML, da_word_map, da_sent_map, "da")
    else:
        print(f"\nSkipping dansk-practice.html (not found)")

    if os.path.exists(SV_HTML):
        patch_html(SV_HTML, sv_word_map, sv_sent_map, "sv")
    else:
        print(f"\nSkipping svensk-practice.html (not found)")

    print("\n✓ All done! Commit everything to GitHub:")
    print("   git add audio/ dansk-practice.html svensk-practice.html")
    print("   git commit -m 'Add pre-generated audio'")
    print("   git push")


if __name__ == "__main__":
    main()
