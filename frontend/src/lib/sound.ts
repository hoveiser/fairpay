// Small Web Audio synth for UI feedback. The AudioContext is created lazily on
// the first user gesture, so browser autoplay policies are respected.
type AnyWindow = Window & { webkitAudioContext?: typeof AudioContext };

let ctx: AudioContext | null = null;
let muted = typeof localStorage !== "undefined" && localStorage.getItem("fairpay.muted") === "1";

function ensure(): AudioContext | null {
  if (typeof window === "undefined") return null;
  if (!ctx) {
    const Ctor = window.AudioContext || (window as AnyWindow).webkitAudioContext;
    if (!Ctor) return null;
    ctx = new Ctor();
  }
  if (ctx.state === "suspended") void ctx.resume();
  return ctx;
}

function tone(
  frequency: number,
  duration: number,
  type: OscillatorType,
  gain: number,
  delay = 0,
) {
  if (muted) return;
  const audio = ensure();
  if (!audio) return;
  const start = audio.currentTime + delay;
  const osc = audio.createOscillator();
  const envelope = audio.createGain();
  osc.type = type;
  osc.frequency.setValueAtTime(frequency, start);
  envelope.gain.setValueAtTime(0.0001, start);
  envelope.gain.exponentialRampToValueAtTime(gain, start + 0.012);
  envelope.gain.exponentialRampToValueAtTime(0.0001, start + duration);
  osc.connect(envelope);
  envelope.connect(audio.destination);
  osc.start(start);
  osc.stop(start + duration + 0.03);
}

export const sound = {
  isMuted: () => muted,
  setMuted(value: boolean) {
    muted = value;
    if (typeof localStorage !== "undefined") {
      localStorage.setItem("fairpay.muted", value ? "1" : "0");
    }
  },
  toggle() {
    sound.setMuted(!muted);
    return muted;
  },
  click() {
    tone(520, 0.045, "triangle", 0.035);
  },
  hover() {
    tone(660, 0.025, "sine", 0.018);
  },
  success() {
    [523.25, 659.25, 783.99].forEach((f, i) => tone(f, 0.14, "sine", 0.04, i * 0.075));
  },
  settle() {
    [392, 523.25, 659.25, 783.99, 1046.5].forEach((f, i) =>
      tone(f, 0.22, "sine", 0.045, i * 0.09),
    );
  },
  error() {
    tone(196, 0.16, "sawtooth", 0.03);
    tone(146.83, 0.2, "sawtooth", 0.025, 0.08);
  },
  step() {
    tone(440, 0.06, "triangle", 0.03);
    tone(587.33, 0.08, "triangle", 0.025, 0.05);
  },
};
