#!/usr/bin/env python3
"""Turn a wav (plus, ideally, the text that produced it) into a timeline.

    python tools/make_timeline.py out.wav --text "привет, как дела" -o out.json

Chatterbox does not expose phoneme timings, but you always know the text you
fed it. Mapping the letter sequence onto the voiced-time axis of the rendered
audio is crude compared to a forced aligner, and on a stylised head it is
indistinguishable. Silences fall out for free: they get no letters, so the
mouth closes.

If you want proper alignment later, replace `letters_to_visemes` with
torchaudio's MMS_FA aligner — the output format is unchanged.

Depends on numpy only.
"""

from __future__ import annotations

import argparse
import json
import wave

import numpy as np

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from neonhead.rig import LETTER_VISEME  # noqa: E402

HOP = 0.02
WIN = 0.04
LONG = set("CDEF")          # vowel-ish visemes hold longer


def read_wav(path: str):
    with wave.open(path, "rb") as wf:
        sr = wf.getframerate()
        ch = wf.getnchannels()
        width = wf.getsampwidth()
        raw = wf.readframes(wf.getnframes())
    if width != 2:
        raise SystemExit("only 16-bit wav is supported; convert first")
    x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0
    if ch > 1:
        x = x.reshape(-1, ch).mean(1)
    return x, sr


def frames(x: np.ndarray, sr: int):
    hop = int(sr * HOP)
    win = int(sr * WIN)
    n = max(1, (len(x) - win) // hop + 1)
    idx = np.arange(win)[None, :] + hop * np.arange(n)[:, None]
    idx = np.clip(idx, 0, len(x) - 1)
    return x[idx]


def prosody(x: np.ndarray, sr: int):
    fr = frames(x, sr)
    rms = np.sqrt((fr ** 2).mean(1) + 1e-12)
    ref = np.percentile(rms, 95) or 1.0
    rms_n = np.clip(rms / ref, 0.0, 1.0)

    # autocorrelation pitch, 70..400 Hz
    lo, hi = int(sr / 400), int(sr / 70)
    f0 = np.zeros(len(fr), np.float32)
    for i, w in enumerate(fr):
        if rms[i] < ref * 0.12:
            continue
        w = w - w.mean()
        ac = np.correlate(w, w, "full")[len(w) - 1:]
        seg = ac[lo:hi]
        if seg.size and ac[0] > 1e-9:
            k = int(np.argmax(seg)) + lo
            if seg.max() / ac[0] > 0.30:
                f0[i] = sr / k

    voiced = f0 > 0
    if voiced.sum() > 4:
        med = float(np.median(f0[voiced]))
        sd = float(np.std(f0[voiced])) or 1.0
        f0n = np.where(voiced, (f0 - med) / sd, 0.0)
    else:
        f0n = np.zeros_like(f0)
    return rms_n.astype(np.float32), np.clip(f0n, -2.5, 2.5).astype(np.float32)


def letters_to_visemes(text: str, rms: np.ndarray, gate: float = 0.10):
    """Lay the letter sequence along the cumulative voiced time of the audio."""
    seq = []
    for ch in text.lower():
        shape = LETTER_VISEME.get(ch)
        if shape is None:
            continue
        if shape == "X":
            if seq and seq[-1][0] == "X":
                continue
            seq.append(("X", 0.0))
        else:
            seq.append((shape, 2.0 if shape in LONG else 1.0))
    if not seq:
        return [{"t": 0.0, "shape": "X"}]

    active = rms > gate
    voiced_time = np.concatenate([[0.0], np.cumsum(active) * HOP])
    total = float(voiced_time[-1]) or (len(rms) * HOP)
    weights = np.array([w for _, w in seq], np.float64)
    if weights.sum() <= 0:
        weights = np.ones(len(seq))
    edges = np.concatenate([[0.0], np.cumsum(weights / weights.sum()) * total])

    out = []
    for (shape, _), start in zip(seq, edges[:-1]):
        k = int(np.searchsorted(voiced_time, start))
        out.append({"t": round(min(k, len(rms) - 1) * HOP, 4), "shape": shape})

    # close the mouth over any silence longer than 120 ms
    silent = ~active
    i = 0
    while i < len(silent):
        if silent[i]:
            j = i
            while j < len(silent) and silent[j]:
                j += 1
            if (j - i) * HOP > 0.12:
                out.append({"t": round(i * HOP, 4), "shape": "X"})
            i = j
        else:
            i += 1
    out.sort(key=lambda d: d["t"])
    return out


def blind_visemes(rms: np.ndarray, x: np.ndarray, sr: int):
    """Fallback when no text is given: energy plus zero-crossing rate."""
    fr = frames(x, sr)
    zcr = (np.diff(np.sign(fr), axis=1) != 0).mean(1)
    out, prev = [], None
    for i, (a, z) in enumerate(zip(rms, zcr)):
        if a < 0.10:
            shape = "X"
        elif z > 0.22:
            shape = "B"
        elif a > 0.72:
            shape = "D"
        elif a > 0.45:
            shape = "C"
        else:
            shape = "E"
        if shape != prev:
            out.append({"t": round(i * HOP, 4), "shape": shape})
            prev = shape
    return out or [{"t": 0.0, "shape": "X"}]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("wav")
    ap.add_argument("--text", default=None, help="the text that was synthesised")
    ap.add_argument("-o", "--out", default=None)
    args = ap.parse_args()

    x, sr = read_wav(args.wav)
    rms, f0 = prosody(x, sr)
    visemes = letters_to_visemes(args.text, rms) if args.text else blind_visemes(rms, x, sr)

    tl = {
        "audio": args.wav,
        "duration": round(len(x) / sr, 4),
        "visemes": visemes,
        "prosody": {"hop": HOP, "rms": [round(float(v), 4) for v in rms],
                    "f0": [round(float(v), 4) for v in f0]},
    }
    out = args.out or (args.wav.rsplit(".", 1)[0] + ".json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(tl, fh, ensure_ascii=False)
    print(f"{out}  {tl['duration']:.2f}s  {len(visemes)} visemes")


if __name__ == "__main__":
    main()
