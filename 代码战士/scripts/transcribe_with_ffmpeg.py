"""Local ASR using ffmpeg PCM input to avoid PyAV decoder incompatibilities."""
from pathlib import Path
import argparse
import json
import subprocess

import numpy as np
from faster_whisper import WhisperModel


def stamp(t):
    ms = round(t * 1000)
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path, help="Output JSON; sibling SRT is also written")
    args = parser.parse_args()
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(args.input), "-f", "s16le",
         "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", "pipe:1"],
        check=True, capture_output=True,
    ).stdout
    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    model = WhisperModel("small", device="cpu", compute_type="int8")
    segments, info = model.transcribe(samples, language="zh", word_timestamps=True, vad_filter=True)
    data = [{"start": s.start, "end": s.end, "text": s.text,
             "words": [{"start": w.start, "end": w.end, "word": w.word} for w in (s.words or [])]}
            for s in segments]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"language": info.language, "segments": data},
                                      ensure_ascii=False, indent=2), encoding="utf-8")
    args.output.with_suffix(".srt").write_text("\n\n".join(
        f"{i}\n{stamp(s['start'])} --> {stamp(s['end'])}\n{s['text'].strip()}"
        for i, s in enumerate(data, 1)) + "\n", encoding="utf-8")
    print(json.dumps(data, ensure_ascii=False))


if __name__ == "__main__":
    main()
