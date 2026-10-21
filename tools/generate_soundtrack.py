#!/usr/bin/env python3
"""Generate the 48 second stereo soundtrack for the Milestone v1 demo.

A soft ambient pad, a slow pulse, and scene-change chimes. Fixed seed, no
external samples. Writes media/milestone_soundtrack.wav (16-bit, 44.1 kHz).
"""
import math
import pathlib
import random
import struct
import wave

RATE = 44100
SECONDS = 48
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "media" / "milestone_soundtrack.wav"

random.seed(7)


def envelope(t, start, attack, release, sustain=1.0):
    if t < start:
        return 0.0
    dt = t - start
    if dt < attack:
        return dt / attack
    if dt < attack + release:
        return 1.0 - (1.0 - sustain) * ((dt - attack) / release)
    return sustain


def pad(t, freq, phase):
    # Slow amplitude movement keeps the pad from sounding static.
    lfo = 0.55 + 0.45 * math.sin(2 * math.pi * 0.045 * t + phase)
    return math.sin(2 * math.pi * freq * t + phase) * lfo


def main():
    frames = []
    total = RATE * SECONDS
    for i in range(total):
        t = i / RATE
        # Pad: A minor with a suspended colour.
        left = (
            0.10 * pad(t, 110.00, 0.0)
            + 0.075 * pad(t, 164.81, 0.7)
            + 0.060 * pad(t, 220.00, 1.4)
            + 0.040 * pad(t, 261.63, 2.1)
        )
        right = (
            0.10 * pad(t, 110.00, 0.4)
            + 0.075 * pad(t, 164.81, 1.1)
            + 0.060 * pad(t, 220.00, 1.8)
            + 0.040 * pad(t, 261.63, 2.5)
        )

        # Soft pulse every two seconds.
        beat = t % 2.0
        if beat < 0.22:
            thump = math.sin(2 * math.pi * 58 * beat) * math.exp(-beat * 14)
            left += 0.055 * thump
            right += 0.055 * thump
        if beat < 0.05:
            tick = math.sin(2 * math.pi * 1200 * beat) * math.exp(-beat * 90)
            left += 0.012 * tick
            right += 0.012 * tick

        # Chimes at each scene change.
        for scene in (6, 12, 18, 24, 30, 36, 42):
            dt = t - scene
            if 0 <= dt < 1.1:
                env = math.exp(-dt * 4.2)
                left += 0.045 * math.sin(2 * math.pi * 523.25 * dt) * env
                left += 0.028 * math.sin(2 * math.pi * 659.25 * dt) * env
                right += 0.045 * math.sin(2 * math.pi * 523.25 * dt + 0.2) * env
                right += 0.028 * math.sin(2 * math.pi * 783.99 * dt) * env

        # Fade in and out.
        fade = min(1.0, t / 2.0, (SECONDS - t) / 3.0)
        left *= fade
        right *= fade

        frames.append(struct.pack("<hh", int(max(-1, min(1, left)) * 26000), int(max(-1, min(1, right)) * 26000)))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(OUT), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(RATE)
        wav.writeframes(b"".join(frames))
    print("wrote", OUT, OUT.stat().st_size, "bytes,", SECONDS, "s, stereo 44.1 kHz")


if __name__ == "__main__":
    main()
