import argparse
import json
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
LOG_FILE = ROOT / "logs" / "imp-tone-log.json"
SIGNATURES_FILE = ROOT / "config" / "imp-voice-signatures.json"

POSITIVE = {"good", "great", "excellent", "happy", "love", "awesome", "nice"}
NEGATIVE = {"bad", "terrible", "sad", "hate", "awful", "angry", "poor"}

def analyze_tone(text: str, speaker: Optional[str] = None) -> dict:
    """Analyze tone and verify speaker identity if provided."""
    lowered = text.lower()
    if any(word in lowered for word in POSITIVE):
        tone = "positive"
    elif any(word in lowered for word in NEGATIVE):
        tone = "negative"
    else:
        tone = "neutral"

    signature = sum(ord(c) for c in text) % 1000
    identity_verified = None
    if speaker:
        try:
            if SIGNATURES_FILE.exists():
                with open(SIGNATURES_FILE, "r", encoding="utf-8") as f:
                    sigs = json.load(f)
            else:
                sigs = {}
        except Exception:
            sigs = {}
        stored = sigs.get(speaker)
        identity_verified = stored == signature or stored is None
        if stored is None:
            sigs[speaker] = signature
            try:
                with open(SIGNATURES_FILE, "w", encoding="utf-8") as f:
                    json.dump(sigs, f, indent=2)
            except Exception:
                pass

    try:
        if LOG_FILE.exists():
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = []
        entry = {"text": text, "tone": tone, "signature": signature}
        if speaker:
            entry["speaker"] = speaker
            entry["identity_verified"] = bool(identity_verified)
        data.append(entry)
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass
    return {"tone": tone, "signature": signature, "identity_verified": bool(identity_verified) if identity_verified is not None else None}

def main():
    parser = argparse.ArgumentParser(description="IMP Tone Analyzer")
    parser.add_argument("text", help="Text to analyze")
    parser.add_argument("--speaker", help="Speaker identifier")
    args = parser.parse_args()
    result = analyze_tone(args.text, args.speaker)
    print(result)

if __name__ == "__main__":
    main()
