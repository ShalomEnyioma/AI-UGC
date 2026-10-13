"""
Showreel soundtrack — composed and synthesized from scratch.

No samples, no generative audio models: every sound below is built from
oscillators, noise and filters with numpy/scipy. The grid is 128 BPM, so
8 bars = exactly 15.000 s, which is the same grid the visuals cut on.

    python3 music.py out.wav
"""
import sys
import wave

import numpy as np
from scipy.signal import fftconvolve, lfilter

SR = 48000
DUR = 15.0
N = int(SR * DUR)
BPM = 128
B = 60 / BPM          # beat   = 0.46875 s
S16 = B / 4           # 16th   = 0.1171875 s
BAR = 4 * B           # bar    = 1.875 s

rng = np.random.default_rng(20261013)


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def tt(n):
    return np.arange(n) / SR


# ---------------------------------------------------------------- buses
dry = np.zeros((N, 2))
verb_send = np.zeros((N, 2))
kick_times = []


def place(sig, t, gain=1.0, pan=0.0, bus=None, send=0.0):
    """Mix a mono or stereo signal into a bus at time t (seconds)."""
    bus = dry if bus is None else bus
    i = int(round(t * SR))
    if i >= N:
        return
    if i < 0:
        sig = sig[-i:]
        i = 0
    n = min(len(sig), N - i)
    if n <= 0:
        return
    if sig.ndim == 1:
        th = (pan + 1) * np.pi / 4
        st = np.stack([sig[:n] * np.cos(th), sig[:n] * np.sin(th)], 1) * np.sqrt(2)
    else:
        st = sig[:n]
    bus[i:i + n] += st * gain
    if send:
        verb_send[i:i + n] += st * gain * send


# ---------------------------------------------------------------- dsp
def biquad(kind, fc, q):
    fc = float(np.clip(fc, 10, SR * 0.45))
    w = 2 * np.pi * fc / SR
    cw, sw = np.cos(w), np.sin(w)
    al = sw / (2 * q)
    if kind == "lp":
        b = [(1 - cw) / 2, 1 - cw, (1 - cw) / 2]
    elif kind == "hp":
        b = [(1 + cw) / 2, -(1 + cw), (1 + cw) / 2]
    else:  # band-pass, constant 0 dB peak
        b = [al, 0.0, -al]
    a = [1 + al, -2 * cw, 1 - al]
    return np.array(b) / a[0], np.array(a) / a[0]


def filt(x, fc, q=0.707, kind="lp", block=64):
    """Biquad with a static or per-sample cutoff (block-wise automation)."""
    if np.isscalar(fc):
        b, a = biquad(kind, fc, q)
        return lfilter(b, a, x, axis=0)
    y = np.empty_like(x)
    zi = np.zeros((2,) + x.shape[1:])
    for s in range(0, len(x), block):
        e = min(s + block, len(x))
        b, a = biquad(kind, fc[(s + e) // 2], q)
        y[s:e], zi = lfilter(b, a, x[s:e], axis=0, zi=zi)
    return y


def saw(freq, n, phase0=None):
    """PolyBLEP band-limited saw. freq may be scalar or per-sample."""
    f = np.broadcast_to(np.asarray(freq, float), (n,))
    dt = f / SR
    ph = (np.cumsum(dt) + (rng.random() if phase0 is None else phase0)) % 1.0
    y = 2 * ph - 1
    m = ph < dt
    x = ph[m] / dt[m]
    y[m] -= x + x - x * x - 1
    m = ph > 1 - dt
    x = (ph[m] - 1) / dt[m]
    y[m] -= x * x + x + x + 1
    return y


def sine(freq, n, phase0=0.0):
    f = np.broadcast_to(np.asarray(freq, float), (n,))
    return np.sin(2 * np.pi * (np.cumsum(f) / SR + phase0))


def noise(n):
    return rng.standard_normal(n)


def adsr(n, a=0.005, d=0.1, s=0.7, r=0.05, hold=None):
    t = tt(n)
    hold = n / SR - r if hold is None else hold
    env = np.where(t < a, t / max(a, 1e-6), s + (1 - s) * np.exp(-(t - a) / max(d, 1e-6)))
    rel = np.clip((t - hold) / r, 0, 1)
    return env * (1 - rel)


# ---------------------------------------------------------------- drums
def kick(dur=0.45):
    n = int(dur * SR)
    t = tt(n)
    f = 44 + 130 * np.exp(-t * 38) + 30 * np.exp(-t * 9)
    body = sine(f, n) * np.exp(-t * 7.5) * np.clip(t / 0.002, 0, 1)
    click = filt(noise(n), 3500, kind="hp") * np.exp(-t * 600) * 0.35
    return np.tanh(1.8 * (body + click)) * 0.9


def clap():
    n = int(0.45 * SR)
    t = tt(n)
    env = sum(np.exp(-np.clip(t - d, 0, None) * 180) * (t >= d) for d in (0, 0.009, 0.019))
    env = env * 0.55 + np.exp(-np.clip(t - 0.028, 0, None) * 17) * (t >= 0.028)
    x = filt(noise(n), 1400, q=1.1, kind="bp") * 2.2 + filt(noise(n), 5200, q=0.8, kind="bp") * 0.7
    body = sine(185 + 40 * np.exp(-t * 60), n) * np.exp(-t * 32) * 0.45
    return np.tanh((x * env + body) * 1.3) * 0.7


def metallic(n):
    # 808-style: six detuned square oscillators at inharmonic ratios
    t = tt(n)
    out = np.zeros(n)
    for f in (205.3, 304.4, 369.6, 522.7, 540.0, 800.0):
        out += np.sign(np.sin(2 * np.pi * f * 2.02 * t + rng.random() * 6.28))
    return out / 6


def hat(open_=False):
    n = int((0.42 if open_ else 0.07) * SR)
    t = tt(n)
    x = filt(metallic(n) * 0.6 + noise(n) * 0.5, 7800, kind="hp")
    x = filt(x, 10500, q=0.9, kind="bp") * 1.4 + x * 0.4
    return x * np.exp(-t * (9 if open_ else 75)) * 0.32


def crash(dur=2.2):
    n = int(dur * SR)
    t = tt(n)
    x = filt(metallic(n) * 0.5 + noise(n), 4200, kind="hp")
    x = x * (np.exp(-t * 2.4) * 0.8 + np.exp(-t * 25) * 0.4)
    return x * 0.28


def tom(f0=130):
    n = int(0.35 * SR)
    t = tt(n)
    f = f0 * (0.55 + 0.45 * np.exp(-t * 18))
    return np.tanh(sine(f, n) * np.exp(-t * 11) * 1.6 + filt(noise(n), 900, kind="lp") * np.exp(-t * 60) * 0.3) * 0.7


def snare():
    n = int(0.22 * SR)
    t = tt(n)
    x = filt(noise(n), 2600, q=0.6, kind="bp") * np.exp(-t * 26)
    body = sine(210 * (1 + 0.4 * np.exp(-t * 50)), n) * np.exp(-t * 30)
    return np.tanh((x * 1.4 + body * 0.7) * 1.2) * 0.55


def boom(dur=2.4):
    """Cinematic sub impact."""
    n = int(dur * SR)
    t = tt(n)
    f = 28 + 46 * np.exp(-t * 3.5)
    x = sine(f, n) * np.exp(-t * 1.6) * np.clip(t / 0.003, 0, 1)
    thump = filt(noise(n), 160, kind="lp") * np.exp(-t * 14) * 2.5
    return np.tanh((x + thump) * 2.0) * 0.8


def tick(f=2600):
    n = int(0.025 * SR)
    t = tt(n)
    return sine(f, n) * np.exp(-t * 260) * 0.35


def whoosh(dur, f0=300, f1=6000, q=1.4):
    n = int(dur * SR)
    t = tt(n) / dur
    fc = f0 * (f1 / f0) ** t
    env = np.sin(np.pi * t) ** 2
    x = filt(noise(n), fc, q=q, kind="bp")
    return np.stack([x, filt(noise(n), fc * 1.07, q=q, kind="bp")], 1) * env[:, None] * 0.9


def riser(dur):
    n = int(dur * SR)
    t = tt(n) / dur
    fc = 250 * (9000 / 250) ** (t ** 1.6)
    nz = filt(noise(n), fc, q=2.2, kind="bp")
    pitch = mtof(53) * 2 ** (2 * t ** 1.4)
    tone = saw(pitch, n) + saw(pitch * 1.006, n) + saw(pitch * 0.994, n)
    tone = filt(tone, fc * 0.6, q=1.0) / 3
    return (nz * 0.8 + tone * 0.25) * (t ** 2.2)


def reverse_crash(dur):
    c = crash(dur)
    return c[::-1] * 1.4


def fm_bell(f, dur=1.6):
    n = int(dur * SR)
    t = tt(n)
    idx = 3.2 * np.exp(-t * 4)
    mod = np.sin(2 * np.pi * f * 3.5 * t) * idx
    car = np.sin(2 * np.pi * f * t + mod)
    return car * np.exp(-t * 2.8) * np.clip(t / 0.002, 0, 1) * 0.3


# ---------------------------------------------------------------- tonal
def supersaw(midis, dur, voices=7, detune=0.22, width=1.0, rel=0.08):
    n = int((dur + rel) * SR)
    L = np.zeros(n)
    R = np.zeros(n)
    for m in midis:
        f = mtof(m)
        for v in range(voices):
            d = (v - (voices - 1) / 2) / ((voices - 1) / 2)
            s = saw(f * 2 ** (d * detune / 12), n)
            p = 0.5 + 0.5 * d * width
            L += s * np.sqrt(1 - p)
            R += s * np.sqrt(p)
    env = adsr(n, a=0.006, d=0.4, s=0.85, r=rel, hold=dur)
    return np.stack([L, R], 1) * env[:, None] / (len(midis) * voices) * 2.2


def pluck(m, dur=0.22, bright=1.0):
    n = int(dur * SR)
    t = tt(n)
    f = mtof(m)
    x = saw(f, n) * 0.6 + saw(f * 1.004, n) * 0.4
    fc = 300 + 5200 * bright * np.exp(-t * 22)
    x = filt(x, fc, q=1.3)
    return x * np.exp(-t * 9) * np.clip(t / 0.002, 0, 1) * 0.5


# chords per bar (bar 7 splits Db | Eb as a IV-V into the final Ab)
FM9 = [53, 56, 60, 63, 67]
EB9 = [51, 55, 58, 63, 65]
DBM7 = [49, 53, 56, 60, 65]
AB9 = [56, 60, 63, 68, 70]
PROG = [(0, FM9, 41), (1, EB9, 39), (2, FM9, 41), (3, DBM7, 37), (4, AB9, 44),
        (5, EB9, 39), (6, DBM7, 37), (6.5, EB9, 39), (7, AB9, 44)]


def chord_at(t):
    cur = PROG[0]
    for p in PROG:
        if t >= p[0] * BAR - 1e-9:
            cur = p
    return cur


def main(out_path):
    # ---------------- drums & percussion schedule
    DROP = 2 * BAR           # 3.75
    FINAL = 7 * BAR          # 13.125

    # intro: typewriter ticks for the "SHOWREEL 2026" HUD type-on
    for k in range(14):
        place(tick(2400 + 300 * (k % 3)), 0.55 + k * 0.045, 0.5, pan=-0.3 + 0.05 * k)
    # the opening dot pop
    place(tick(1200) * 2, 0.10, 0.9)
    place(whoosh(0.45, 600, 7000, q=2.5), 0.40, 0.25)

    # bar 2: six letters slam in on 8ths
    for k in range(6):
        place(tom(150 - k * 6), BAR + k * B / 2, 0.9, pan=(k - 2.5) * 0.12, send=0.15)
        place(kick(0.25), BAR + k * B / 2, 0.35)
    # snare build, 16ths accelerating in volume
    for k in range(4):
        place(snare(), BAR + 6 * B / 2 + k * S16, 0.25 + 0.12 * k, send=0.2)
    # zoom-through-the-O: reverse crash + whoosh, then a hard gap before the drop
    place(reverse_crash(0.47), DROP - 0.47, 0.9)
    place(whoosh(0.5, 400, 9000, q=1.2), DROP - 0.5, 0.6)
    place(riser(DROP - 0.05), 0.0, 0.5)

    # main groove: bars 3-7
    for bar in range(2, 7):
        for beat in range(4):
            t0 = bar * BAR + beat * B
            place(kick(), t0, 1.0)
            kick_times.append(t0)
            if beat in (1, 3):
                place(clap(), t0, 0.8, send=0.25)
            # open hat on the off-beat
            place(hat(True), t0 + B / 2, 0.8, pan=0.25)
            for s in range(4):
                if s == 2:
                    continue
                vel = (0.9, 0.45, 0, 0.6)[s]
                place(hat(), t0 + s * S16, vel * 1.4, pan=-0.2)
    # snare roll + riser into the final hit (last 2 beats of bar 7)
    for k in range(16):
        tk = 6 * BAR + 2 * B + k * (B / 8)
        place(snare(), tk, 0.18 + 0.03 * k, send=0.25)
    place(riser(2 * B - 0.06), 6 * BAR + 2 * B, 0.3)
    place(reverse_crash(0.6), FINAL - 0.6, 0.6)

    # transition swooshes on every scene change
    for tb in (3, 4, 5, 6):
        place(whoosh(0.32, 900, 8000, q=1.8), tb * BAR - 0.26, 0.28)
    # crashes on section starts
    for tb in (2, 5):
        place(crash(), tb * BAR, 0.9, send=0.2)

    # final hit
    place(kick(), FINAL, 1.1)
    place(boom(), FINAL, 0.45)
    place(crash(3.0), FINAL, 1.1, send=0.4)
    place(clap(), FINAL, 0.7, send=0.6)

    # ---------------- tonal layers
    # pad: continuous chords, filtered open over the intro, pumping afterwards
    pad = np.zeros((N, 2))
    for i, (bar, ch, root) in enumerate(PROG[:-1]):
        nxt = PROG[i + 1][0]
        s = supersaw(ch, (nxt - bar) * BAR, rel=0.06)
        place(s, bar * BAR, 1.0, bus=pad)
    t = tt(N)
    cutoff = np.where(t < DROP, 350 * (3200 / 350) ** (t / DROP) ** 2, 4200)
    cutoff = np.where((t > 5 * BAR) & (t < 6 * BAR), 4200 + 2500 * np.sin(np.pi * (t - 5 * BAR) / BAR), cutoff)
    pad = filt(pad, cutoff, q=0.9)
    # sidechain pump from the kicks
    sc = np.ones(N)
    for k in kick_times:
        i = int(k * SR)
        n = min(int(B * SR), N - i)
        x = tt(n)
        sc[i:i + n] = np.minimum(sc[i:i + n], 1 - 0.78 * np.exp(-x / 0.11) * (1 - np.clip((x - 0.25) / 0.1, 0, 1)))
    # trance gate on bar 7 (montage) — 16th chops
    gate = np.ones(N)
    m = (t >= 6 * BAR) & (t < FINAL)
    ph = ((t[m] - 6 * BAR) / S16) % 1
    gate[m] = np.where(ph < 0.55, 1.0, 0.12)
    pad *= (sc * gate)[:, None]
    # silence right before the drops (the classic "gap")
    for g0, g1 in ((DROP - 0.06, DROP), (FINAL - 0.07, FINAL)):
        pad[int(g0 * SR):int(g1 * SR)] = 0
    dry[:int(FINAL * SR)] += pad[:int(FINAL * SR)] * 0.95
    verb_send[:int(FINAL * SR)] += pad[:int(FINAL * SR)] * 0.12

    # rolling bass, 16ths minus the kick slot
    for bar in range(2, 7):
        for beat in range(4):
            for s in (1, 2, 3):
                ts = bar * BAR + beat * B + s * S16
                _, _, root = chord_at(ts)
                n = int(S16 * 0.95 * SR)
                x = tt(n)
                f = mtof(root)
                tone = saw(f, n) * 0.7 + np.sign(np.sin(2 * np.pi * f * x)) * 0.3
                tone = filt(tone, 220 + 1600 * np.exp(-x * 30), q=1.4)
                sub = sine(f / 2, n) * 0.45
                env = np.clip(x / 0.003, 0, 1) * np.clip((n / SR - x) / 0.01, 0, 1)
                place((tone * 0.8 + sub) * env, ts, 0.5)

    # arp from bar 4 (the 3D scene) through bar 6
    pattern = [0, 2, 4, 1, 3, 2, 4, 3]
    for k in range(3 * 16):
        ts = 3 * BAR + k * S16
        _, ch, _ = chord_at(ts)
        note = sorted(ch)[pattern[k % 8]] + 12
        bright = 0.5 + 0.5 * (k / 48)
        p = pluck(note, 0.3, bright)
        place(p, ts, 0.9, pan=0.35 if k % 2 else -0.35, send=0.35)
        # dotted-8th ping-pong echo
        for e in range(1, 4):
            place(p, ts + e * 3 * S16, 0.9 * 0.42 ** e, pan=(-1) ** e * 0.7, send=0.3)

    # montage stabs: one chord stab per visual cut (8ths of bar 7)
    for k in range(8):
        ts = 6 * BAR + k * B / 2
        _, ch, _ = chord_at(ts)
        s = supersaw([m + 12 for m in ch], B / 2 * 0.55, voices=5, detune=0.3, rel=0.04)
        s = filt(s, 5200, q=0.8)
        place(s, ts, 0.9, send=0.3)

    # final chord: wide, bright, long tail
    fin = supersaw(AB9 + [44, 51], DUR - FINAL, voices=9, detune=0.28, rel=0.01)
    tf = tt(len(fin))
    fin = filt(fin, 900 + 6000 * np.exp(-tf * 1.4), q=0.8)
    fin *= np.exp(-tf * 0.9)[:, None]
    place(fin, FINAL, 1.6, send=0.45)
    nf = int((DUR - FINAL) * SR)
    sub = sine(mtof(32), nf) * np.exp(-tt(nf) * 1.2) * 0.5
    place(sub, FINAL, 0.35)
    # bells sparkle over the logo lockup
    for i, (dt_, m) in enumerate([(0.0, 87), (0.235, 84), (0.47, 82), (0.705, 80), (0.94, 75), (1.17, 80)]):
        place(fm_bell(mtof(m), 1.6), FINAL + 0.12 + dt_, 0.8, pan=(-0.4, 0.4)[i % 2], send=0.6)

    # ---------------- reverb (synthesized impulse: decaying filtered noise)
    ir_n = int(2.4 * SR)
    ti = tt(ir_n)
    ir = np.stack([noise(ir_n), noise(ir_n)], 1) * np.exp(-ti * 2.6)[:, None]
    ir = filt(ir, 5000) * 0.5 + filt(ir, 900) * 0.5
    ir[: int(0.012 * SR)] = 0  # pre-delay
    ir /= np.sqrt((ir ** 2).sum() / 2)
    wet = np.stack([fftconvolve(verb_send[:, c], ir[:, c])[:N] for c in range(2)], 1)
    wet = filt(wet, 250, kind="hp")

    mix = dry + wet * 0.32
    mix = filt(mix, 28, kind="hp")
    # gentle glue + soft clip
    mix = np.tanh(mix * 1.15) / np.tanh(1.15)
    peak = np.abs(mix).max()
    mix *= 0.891 / peak  # -1 dBFS
    fade = int(0.04 * SR)
    mix[-fade:] *= np.linspace(1, 0, fade)[:, None]

    rms = np.sqrt((mix ** 2).mean())
    print(f"peak -1.0 dBFS, rms {20 * np.log10(rms):.1f} dBFS, {len(mix) / SR:.3f}s")
    pcm = (np.clip(mix, -1, 1) * 32767).astype("<i2")
    with wave.open(out_path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "music.wav")
