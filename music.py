"""Background music: every part of the game has its own track.

* "master"   - the kung fu song (file), for Kung-Fu-Meister
* "menu", "bubbles", "animals", "dressup" - short loops composed in code (no extra files),
  rendered once at start-up and played as seamless loops.
"""
import glob
import os

import numpy as np
import pygame

_ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "music")

FILES = {
    "master": ("AgenChicken - Japanese DnB.ogg", 0.35),   # the kung fu song
}
VOLUME = {"menu": 0.30, "bubbles": 0.28, "animals": 0.30, "dressup": 0.30, "pizza": 0.30, "car": 0.30}

_NOTE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def _hz(name: str) -> float:
    """'A4' / 'F#3' / 'Bb2' -> frequency."""
    n = _NOTE[name[0]]
    i = 1
    while name[i] in "#b":
        n += 1 if name[i] == "#" else -1
        i += 1
    octave = int(name[i:])
    return 440.0 * 2 ** ((n - 9 + 12 * (octave - 4)) / 12)


class _Loop:
    """Mixes notes into one fixed-length buffer; notes running past the end wrap around,
    so the loop is seamless."""

    def __init__(self, sr: int, seconds: float) -> None:
        self.sr = sr
        self.buf = np.zeros(int(sr * seconds), np.float64)

    def add(self, start: float, wave: np.ndarray) -> None:
        n, i = len(self.buf), int(start * self.sr) % len(self.buf)
        first = min(len(wave), n - i)
        self.buf[i:i + first] += wave[:first]
        if first < len(wave):
            rest = min(len(wave) - first, n)
            self.buf[:rest] += wave[first:first + rest]

    def result(self, peak: float = 0.7) -> np.ndarray:
        return self.buf * (peak / max(1e-9, float(np.max(np.abs(self.buf)))))


def _t(sr, dur):
    return np.arange(int(sr * dur)) / sr


def _pluck(sr, f, dur=0.5, vol=0.4, bright=1.0):
    t = _t(sr, dur)
    w = np.sin(2 * np.pi * f * t) + 0.35 * bright * np.sin(4 * np.pi * f * t) \
        + 0.12 * bright * np.sin(6 * np.pi * f * t)
    return w * np.exp(-t * 7.0) * np.minimum(1, t * 400) * vol


def _bell(sr, f, dur=1.2, vol=0.3):
    t = _t(sr, dur)
    w = np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 2.76 * t) \
        + 0.25 * np.sin(2 * np.pi * f * 5.4 * t)
    return w * np.exp(-t * 3.2) * np.minimum(1, t * 600) * vol


def _pad(sr, f, dur=2.0, vol=0.18):
    t = _t(sr, dur)
    w = sum(np.sin(2 * np.pi * f * d * t + k) for k, d in enumerate((0.997, 1.0, 1.004)))
    env = np.minimum(1, t / 0.5) * np.minimum(1, (dur - t) / 0.6)
    return w / 3 * env * vol


def _tri(sr, f, dur=0.25, vol=0.3):
    t = _t(sr, dur)
    w = 2 * np.abs(2 * ((f * t) % 1) - 1) - 1
    return w * np.exp(-t * 9.0) * np.minimum(1, t * 500) * vol


def _bass(sr, f, dur=0.4, vol=0.45):
    t = _t(sr, dur)
    w = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)
    return w * np.exp(-t * 5.0) * np.minimum(1, t * 300) * vol


def _hat(sr, rnd, dur=0.05, vol=0.12):
    t = _t(sr, dur)
    n = rnd.uniform(-1, 1, len(t))
    n = n - np.convolve(n, np.ones(6) / 6, mode="same")      # crude high-pass
    return n * np.exp(-t * 90) * vol


def _kick(sr, dur=0.22, vol=0.5):
    t = _t(sr, dur)
    f = 55 + 90 * np.exp(-t * 28)
    return np.sin(2 * np.pi * np.cumsum(f) / sr) * np.exp(-t * 14) * vol


def _compose(style: str, sr: int) -> np.ndarray:
    rnd = np.random.RandomState({"menu": 3, "bubbles": 7, "animals": 11, "dressup": 5, "pizza": 13, "car": 17}[style])
    if style == "menu":                    # bright and welcoming
        bpm, bars = 108, 8
        prog = [("C3", ["C4", "E4", "G4", "A4", "C5"]), ("A2", ["A3", "C4", "E4", "G4", "A4"]),
                ("F2", ["F3", "A3", "C4", "E4", "G4"]), ("G2", ["G3", "B3", "D4", "F4", "G4"])]
        lead, step = "bell", 0.5
    elif style == "bubbles":               # airy marimba plinks
        bpm, bars = 92, 8
        prog = [("D3", ["D4", "F#4", "A4", "B4", "D5"]), ("B2", ["B3", "D4", "F#4", "A4", "B4"]),
                ("G2", ["G3", "B3", "D4", "F#4", "A4"]), ("A2", ["A3", "C#4", "E4", "F#4", "A4"])]
        lead, step = "pluck", 0.5
    elif style == "animals":               # calm yoga pads and soft plucks
        bpm, bars = 66, 8
        prog = [("F2", ["F3", "A3", "C4", "D4", "F4"]), ("D2", ["D3", "F3", "A3", "C4", "D4"]),
                ("Bb2", ["Bb3", "D4", "F4", "G4", "Bb4"]), ("C3", ["C4", "E4", "G4", "A4", "C5"])]
        lead, step = "pluck", 1.0
    elif style == "car":                   # driving beat: steady kick, bright arpeggios
        bpm, bars = 138, 8
        prog = [("C3", ["C4", "E4", "G4", "B4", "C5"]), ("G2", ["G3", "B3", "D4", "F#4", "G4"]),
                ("A2", ["A3", "C4", "E4", "G4", "A4"]), ("F2", ["F3", "A3", "C4", "E4", "F4"])]
        lead, step = "tri", 0.5
    elif style == "pizza":                 # bouncy mandolin-like plucks in A minor
        bpm, bars = 134, 8
        prog = [("A2", ["A3", "C4", "E4", "G4", "A4"]), ("D3", ["D4", "F4", "A4", "C5", "D5"]),
                ("E2", ["E3", "G#3", "B3", "D4", "E4"]), ("A2", ["A3", "C4", "E4", "A4", "C5"])]
        lead, step = "pluck", 0.5
    else:                                  # dressup: playful and bouncy
        bpm, bars = 124, 8
        prog = [("G2", ["G3", "B3", "D4", "E4", "G4"]), ("E2", ["E3", "G3", "B3", "D4", "E4"]),
                ("C3", ["C4", "E4", "G4", "A4", "C5"]), ("D3", ["D4", "F#4", "A4", "B4", "D5"])]
        lead, step = "tri", 0.5

    beat = 60.0 / bpm
    loop = _Loop(sr, bars * 4 * beat)
    for bar in range(bars):
        root, scale = prog[bar % len(prog)]
        t0 = bar * 4 * beat
        if style == "animals":
            for f in (root, scale[0], scale[2]):
                loop.add(t0, _pad(sr, _hz(f), 4 * beat * 1.15))
        else:
            loop.add(t0, _pad(sr, _hz(scale[0]), 4 * beat * 1.05, 0.10))
        # bass
        for b in range(4):
            if style in ("menu", "dressup", "pizza", "car") or b in (0, 2):
                off = 0.5 if style in ("dressup", "pizza") and b % 2 else 0.0
                loop.add(t0 + (b + off) * beat, _bass(sr, _hz(root), beat * 0.9))
        # lead melody: random walk over the chord tones
        idx = rnd.randint(len(scale))
        n_steps = int(4 / step)
        for k in range(n_steps):
            if rnd.rand() < 0.22:
                continue
            idx = int(np.clip(idx + rnd.choice([-2, -1, -1, 0, 1, 1, 2]), 0, len(scale) - 1))
            f = _hz(scale[idx])
            at = t0 + k * step * beat
            if lead == "bell":
                loop.add(at, _bell(sr, f))
            elif lead == "tri":
                loop.add(at, _tri(sr, f))
            else:
                loop.add(at, _pluck(sr, f, 0.7 if style == "animals" else 0.5))
        # percussion
        if style in ("menu", "dressup", "pizza", "car"):
            for k in range(8):
                loop.add(t0 + k * 0.5 * beat, _hat(sr, rnd, vol=0.10 if k % 2 else 0.06))
            if style in ("dressup", "car"):
                for b in ((0, 2) if style == "dressup" else (0, 1, 2, 3)):
                    loop.add(t0 + b * beat, _kick(sr, vol=0.35))
    return loop.result()


class MusicPlayer:
    """play(name) switches tracks (with a short fade). Safe to call without audio."""

    def __init__(self) -> None:
        self.enabled = bool(pygame.mixer.get_init())
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        self._channel: pygame.mixer.Channel | None = None
        self.current: str | None = None
        if self.enabled:
            self._render()

    def _render(self) -> None:
        sr = pygame.mixer.get_init()[0]
        for style in ("menu", "bubbles", "animals", "dressup", "pizza", "car"):
            mono = _compose(style, sr)
            pcm = np.ascontiguousarray(
                np.column_stack([mono, mono]) * 32000).astype(np.int16)
            snd = pygame.mixer.Sound(buffer=pcm.tobytes())
            snd.set_volume(VOLUME[style])
            self._sounds[style] = snd

    def play(self, name: str) -> None:
        if not self.enabled or name == self.current:
            return
        self.stop()
        self.current = name
        if name in self._sounds:
            self._channel = self._sounds[name].play(loops=-1, fade_ms=500)
            return
        fname, vol = FILES.get(name, (None, 0.3))
        path = os.path.join(_ASSETS, fname) if fname else None
        if path and os.path.exists(path):
            try:
                pygame.mixer.music.load(path)
                pygame.mixer.music.set_volume(vol)
                pygame.mixer.music.play(-1, fade_ms=500)
            except pygame.error:
                pass

    def stop(self) -> None:
        if not self.enabled:
            return
        pygame.mixer.music.fadeout(300)
        if self._channel is not None:
            self._channel.fadeout(300)
            self._channel = None
        self.current = None
