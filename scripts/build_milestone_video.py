#!/usr/bin/env python3
"""Build the 48s Milestone v1 demo video.

Input: frontend/shots/milestone_frames (720 JPEGs at 15 fps, 1280x720).
Audio: media/milestone_soundtrack.wav from tools/generate_soundtrack.py.
Output: docs/demo-video-subtitled.mp4 and frontend/public/demo-video-subtitled.mp4.
"""
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
FRAMES = ROOT / "frontend" / "shots" / "milestone_frames"
AUDIO = ROOT / "media" / "milestone_soundtrack.wav"
ASS = ROOT / "media" / "milestone_demo.ass"
DRAFT = ROOT / "media" / "milestone_demo.mp4"
DOCS_OUT = ROOT / "docs" / "demo-video-subtitled.mp4"
PUBLIC_OUT = ROOT / "frontend" / "public" / "demo-video-subtitled.mp4"

W, H = 1280, 720
FPS_IN, FPS_OUT = 15, 30
SECONDS = 48

# (start, end, heading, body lines)
CAPTIONS = [
    (0, 6, "FairPay Milestone v1",
     ["A funded payroll vault that cannot be raided",
      "Every agreement locks 100% of max liability before work starts"]),
    (6, 12, "Live what-if simulator",
     ["Move base pay, bonus cap, appeal bond, and the 0/50/80/100 anchor",
      "The band and the worker/employer split follow the contract's integer rules"]),
    (12, 18, "PAPITO maximum-liability lock",
     ["The full max liability stays in vault custody through submission, audit, and appeal",
      "Employer surplus recovery reverts while the window is open"]),
    (18, 24, "Two-party timeline",
     ["OPEN, SUBMITTED, AUDITED, APPEALED or CO-SIGNED, SETTLED",
      "A single signature never moves funds"]),
    (24, 30, "Consensus inspector",
     ["The model scores delivery; the contract quantizes it onto 0, 50, 80, 100",
      "Validators must agree exactly on band, anchor, and authenticity"]),
    (30, 36, "Security guard lab",
     ["Premature surplus clawback reverts with liability locked",
      "Single-party co-sign moves zero funds; post-settlement mutation reverts"]),
    (36, 42, "Live StudioNet reads",
     ["Vault, locks, bonds, and the invariant come from the deployed contract",
      "Four to five gen_call requests on load, no polling"]),
    (42, 48, "Verified on StudioNet",
     ["179 Direct Mode tests, byte-identical source, four-way sha256",
      "github.com/hoveiser/fairpay"]),
]

HEADER = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,DejaVu Sans,24,&H00FFFFFF,&H00FFFFFF,&H00000000,&H70000000,0,0,0,0,100,100,0,0,3,11,0,2,60,60,18,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def ts(sec):
    return f"{int(sec // 3600)}:{int((sec % 3600) // 60):02d}:{sec % 60:05.2f}"


def build_ass():
    events = []
    for start, end, heading, body in CAPTIONS:
        lines = [f"{{\\b1\\fs31}}{heading}{{\\b0\\fs24}}"] + body
        text = "\\N".join(lines)
        events.append(f"Dialogue: 0,{ts(start)},{ts(end)},Cap,,0,0,0,,{text}\n")
    ASS.write_text(HEADER + "".join(events), encoding="utf-8")


def run(cmd):
    print("+", " ".join(str(x) for x in cmd[:8]), "...")
    result = subprocess.run([str(x) for x in cmd], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if result.returncode != 0:
        print(result.stdout[-4000:])
        sys.exit("ffmpeg failed")


def main():
    if not FRAMES.exists() or len(list(FRAMES.glob("*.jpg"))) < FPS_IN * SECONDS:
        sys.exit("missing frames; run node frontend/capture_milestone.mjs first")
    if not AUDIO.exists():
        run([sys.executable, str(ROOT / "tools" / "generate_soundtrack.py")])
    build_ass()
    vf = (
        f"fade=t=in:st=0:d=0.4,fade=t=out:st={SECONDS - 0.6}:d=0.6,"
        f"subtitles={ASS}"
    )
    run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-framerate", str(FPS_IN), "-start_number", "0", "-i", str(FRAMES / "%05d.jpg"),
        "-i", str(AUDIO),
        "-vf", vf, "-r", str(FPS_OUT), "-t", str(SECONDS),
        "-c:v", "libx264", "-preset", "medium", "-crf", "24", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-ac", "2",
        "-movflags", "+faststart", "-shortest", str(DRAFT),
    ])
    DOCS_OUT.parent.mkdir(parents=True, exist_ok=True)
    PUBLIC_OUT.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(DRAFT, DOCS_OUT)
    shutil.copyfile(DRAFT, PUBLIC_OUT)
    size = DOCS_OUT.stat().st_size
    print("wrote", DOCS_OUT.relative_to(ROOT), f"({size / 1e6:.2f} MB)")
    print("wrote", PUBLIC_OUT.relative_to(ROOT))
    if size >= 10_000_000:
        sys.exit("video is 10 MB or larger")


if __name__ == "__main__":
    main()
