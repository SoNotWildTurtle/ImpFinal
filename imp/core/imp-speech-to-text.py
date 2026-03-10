import argparse
import json
from pathlib import Path
import importlib.util

try:
    import speech_recognition as sr
except ImportError:
    sr = None
ROOT = Path(__file__).resolve().parents[1]
LOG_FILE = ROOT / "logs" / "imp-speech-log.txt"

def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

_tone = _load("imp_tone_analyzer", ROOT / "core" / "imp-tone-analyzer.py")
analyze_tone = _tone.analyze_tone

def transcribe(audio_file=None, duration=None, offline=False, speaker=None):
    """Transcribe audio either online or with a local fallback."""
    if sr is None:
        print("[!] speech_recognition not installed")
        return ""

    r = sr.Recognizer()
    if audio_file:
        with sr.AudioFile(audio_file) as source:
            audio = r.record(source)
    else:
        with sr.Microphone() as source:
            if duration:
                audio = r.record(source, duration=duration)
            else:
                audio = r.listen(source)

    text = ""
    if offline:
        try:
            text = r.recognize_sphinx(audio)
        except Exception:
            text = ""
    else:
        try:
            text = r.recognize_google(audio)
        except Exception:
            try:
                text = r.recognize_sphinx(audio)
            except Exception:
                text = ""
    if text:
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(text + "\n")
        except Exception:
            pass
        print(text)
        try:
            analysis = analyze_tone(text, speaker)
            print(f"tone: {analysis['tone']}")
            if speaker and analysis.get("identity_verified") is False:
                print("identity mismatch")
        except Exception:
            pass
    return text

def main():
    parser = argparse.ArgumentParser(description="IMP Speech-to-Text")
    parser.add_argument("--file", help="Audio file to transcribe")
    parser.add_argument("--duration", type=int, help="Record time in seconds")
    parser.add_argument("--check", action="store_true", help="Check library availability only")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Use offline transcription with PocketSphinx if available",
    )
    parser.add_argument("--speaker", help="Speaker identifier")
    args = parser.parse_args()
    if args.check:
        if sr is None:
            print("[!] speech_recognition not installed")
        else:
            print("speech_recognition ready")
        return
    transcribe(args.file, args.duration, offline=args.offline, speaker=args.speaker)

if __name__ == "__main__":
    main()
