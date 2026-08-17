"""Timeline playback.

Sync is driven by the audio stream position, never by wall-clock time since
`play()` — that drift is the classic lip-sync bug. If sounddevice is missing
the timeline still animates against a monotonic clock, just without sound.
"""

from __future__ import annotations

import json
import threading
import time
import wave

import numpy as np

try:
    import sounddevice as sd
except Exception:                                    # optional dependency
    sd = None


class Player:
    def __init__(self):
        self.active = False
        self.visemes: list[tuple[float, str]] = []
        self.rms = np.zeros(1, np.float32)
        self.f0 = np.zeros(1, np.float32)
        self.hop = 0.02
        self.duration = 0.0
        self._frames = 0
        self._sr = 24000
        self._stream = None
        self._t0 = 0.0
        self._lock = threading.Lock()
        self._idx = 0

    # -- control -----------------------------------------------------------

    def load(self, timeline_path: str, wav_path: str | None = None, play_audio=True):
        with open(timeline_path, "r", encoding="utf-8") as fh:
            tl = json.load(fh)
        self.load_data(tl, wav_path, play_audio)

    def load_data(self, tl: dict, wav_path: str | None = None, play_audio=True):
        self.stop()

        self.visemes = sorted(
            (float(v["t"]), str(v.get("shape", "X")).upper()) for v in tl.get("visemes", []))
        pros = tl.get("prosody", {})
        self.hop = float(pros.get("hop", 0.02))
        self.rms = np.asarray(pros.get("rms", [0.0]), np.float32)
        self.f0 = np.asarray(pros.get("f0", [0.0]), np.float32)
        self.duration = float(tl.get("duration",
                                     max(len(self.rms) * self.hop,
                                         self.visemes[-1][0] if self.visemes else 0.0)))
        self._idx = 0
        wav = wav_path or tl.get("audio")

        if play_audio and sd is not None and wav:
            try:
                self._start_audio(wav)
            except Exception:
                self._stream = None
        if self._stream is None:
            self._t0 = time.monotonic()
        self.active = True

    def _start_audio(self, path: str):
        with wave.open(path, "rb") as wf:
            self._sr = wf.getframerate()
            ch = wf.getnchannels()
            raw = wf.readframes(wf.getnframes())
        data = np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0
        if ch > 1:
            data = data.reshape(-1, ch)
        else:
            data = data.reshape(-1, 1)
        self._data = data
        self._frames = 0
        self.duration = max(self.duration, len(data) / self._sr)

        def cb(outdata, frames, time_info, status):
            i = self._frames
            block = self._data[i:i + frames]
            n = len(block)
            outdata[:n] = block
            if n < frames:
                outdata[n:] = 0.0
            with self._lock:
                self._frames = i + n
            if n == 0:
                raise sd.CallbackStop

        self._stream = sd.OutputStream(
            samplerate=self._sr, channels=data.shape[1], callback=cb, blocksize=512)
        self._stream.start()

    def stop(self):
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        self.active = False

    # -- per-frame ---------------------------------------------------------

    def playhead(self) -> float:
        if self._stream is not None:
            with self._lock:
                pos = self._frames / float(self._sr)
            return max(0.0, pos - float(self._stream.latency or 0.0))
        return time.monotonic() - self._t0

    def sample(self):
        """Returns (viseme_shape_or_None, rms, f0_normalised). None when finished."""
        if not self.active:
            return None
        t = self.playhead()
        if t > self.duration + 0.20:
            self.stop()
            return None

        shape = None
        while self._idx < len(self.visemes) and self.visemes[self._idx][0] <= t:
            shape = self.visemes[self._idx][1]
            self._idx += 1

        k = int(t / self.hop)
        rms = float(self.rms[k]) if 0 <= k < len(self.rms) else 0.0
        f0 = float(self.f0[k]) if 0 <= k < len(self.f0) else 0.0
        return shape, rms, f0
