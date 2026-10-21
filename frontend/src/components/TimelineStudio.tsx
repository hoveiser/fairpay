import { useEffect, useState } from "react";
import {
  Check,
  ChevronRight,
  Clock3,
  Gavel,
  Handshake,
  Lock,
  Play,
  RotateCcw,
  ShieldCheck,
  Unlock,
} from "lucide-react";
import { sound } from "../lib/sound";
import type { Role } from "../lib/wallet";

interface Props {
  role: Role;
}

type Branch = "appeal" | "cosign";

const STEPS = [
  {
    key: "OPEN",
    title: "Agreement opened and funded",
    detail:
      "The employer moves the full max liability (base plus bonus cap) from its FPT balance into vault custody. Nothing is releasable yet.",
    actor: "Employer funds, vault locks",
    lock: 80,
  },
  {
    key: "SUBMITTED",
    title: "Worker submits a tranche",
    detail:
      "The worker submits hours, a timesheet, and commit-pinned evidence. The evidence seal is produced by strict validator agreement.",
    actor: "Worker submits",
    lock: 80,
  },
  {
    key: "AUDITED",
    title: "Consensus audit, appeal window locked",
    detail:
      "Validators agree on the payroll band, delivery anchor, and evidence authenticity. The full max liability stays locked through the appeal clock.",
    actor: "Consensus decides, nobody overrides",
    lock: 80,
  },
  {
    key: "APPEALED / CO-SIGNED",
    title: "Appeal or two-party fast track",
    detail:
      "The worker may appeal and post the bond, or both parties may co-sign the exact same payout bps. A single party alone never moves funds.",
    actor: "Worker appeal, or both parties co-sign",
    lock: 80,
  },
  {
    key: "SETTLED",
    title: "Settlement receipt issued",
    detail:
      "The worker receives the final payout, the employer receives the remaining surplus, and the vault release is recorded in an immutable receipt.",
    actor: "Permissionless settlement",
    lock: 0,
  },
];

export default function TimelineStudio({ role }: Props) {
  const [step, setStep] = useState(0);
  const [branch, setBranch] = useState<Branch>("cosign");
  const [playing, setPlaying] = useState(false);

  useEffect(() => {
    if (!playing) return;
    if (step >= STEPS.length - 1) {
      setPlaying(false);
      return;
    }
    const timer = window.setTimeout(() => {
      sound.step();
      setStep((value) => value + 1);
      if (step === 2) setBranch("cosign");
    }, 1100);
    return () => window.clearTimeout(timer);
  }, [playing, step]);

  const current = STEPS[step];
  const bond = branch === "appeal" && step === 3 ? 2 : 0;
  const locked = step === 4 ? 0 : current.lock + bond;

  function advance() {
    if (step >= STEPS.length - 1) return;
    sound.step();
    setStep((value) => value + 1);
  }

  function reset() {
    sound.click();
    setPlaying(false);
    setStep(0);
    setBranch("cosign");
  }

  return (
    <div className="rounded-3xl bg-white/[0.03] p-5 ring-1 ring-white/10 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Clock3 size={18} className="text-cyan-300" />
            <h3 className="text-base font-bold text-white">Two-party timeline studio</h3>
          </div>
          <p className="mt-1 max-w-2xl text-xs leading-relaxed text-slate-400">
            Walk the exact settlement path. The lock badge follows the PAPITO rule: the
            employer cannot recover unearned surplus until every tranche is final.
          </p>
        </div>
        <div
          className={
            "flex items-center gap-2 rounded-full px-3 py-1.5 text-[11px] font-bold ring-1 " +
            (step === 4
              ? "bg-emerald-500/10 text-emerald-200 ring-emerald-400/30"
              : "bg-amber-500/10 text-amber-200 ring-amber-400/30")
          }
        >
          {step === 4 ? <Unlock size={13} /> : <Lock size={13} />}
          {step === 4 ? "Surplus released" : locked.toFixed(0) + " GEN locked"}
        </div>
      </div>

      <div className="relative mt-7">
        <div className="absolute left-4 right-4 top-4 h-px bg-white/10" />
        <div
          className="absolute left-4 top-4 h-px bg-gradient-to-r from-violet-500 to-cyan-400 transition-all duration-700"
          style={{ width: "calc(" + (step / (STEPS.length - 1)) * 100 + "% - 1rem)" }}
        />
        <div className="relative grid grid-cols-5 gap-1">
          {STEPS.map((item, index) => {
            const done = index < step;
            const active = index === step;
            const label = index === 3 ? (branch === "appeal" ? "APPEALED" : "CO-SIGNED") : item.key;
            return (
              <div key={item.key} className="flex flex-col items-center text-center">
                <div
                  className={
                    "z-10 flex h-8 w-8 items-center justify-center rounded-full text-[11px] font-bold ring-2 transition " +
                    (done
                      ? "bg-violet-500 text-white ring-violet-400"
                      : active
                        ? "bg-[#0a1020] text-violet-200 ring-violet-400"
                        : "bg-[#0a1020] text-slate-500 ring-white/10")
                  }
                >
                  {done ? <Check size={14} /> : index + 1}
                </div>
                <div
                  className={
                    "mt-2 text-[9px] font-bold uppercase leading-tight tracking-wider sm:text-[10px] " +
                    (active ? "text-white" : done ? "text-violet-200" : "text-slate-500")
                  }
                >
                  {label}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="mt-6 grid gap-3 lg:grid-cols-[1.4fr_1fr]">
        <div className="rounded-2xl bg-[#0a1020] p-4 ring-1 ring-white/10">
          <div className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-wider text-violet-200">
            <ShieldCheck size={13} />
            Step {step + 1} of {STEPS.length}
          </div>
          <div className="mt-1.5 text-sm font-bold text-white">{current.title}</div>
          <p className="mt-1.5 text-xs leading-relaxed text-slate-400">{current.detail}</p>
          <div className="mt-3 flex flex-wrap items-center gap-2 text-[10px]">
            <span className="rounded bg-white/5 px-2 py-1 font-mono text-slate-300">
              actor: {role.toLowerCase() === "worker" && step === 1 ? "worker (you)" : current.actor}
            </span>
            <span className="rounded bg-white/5 px-2 py-1 font-mono text-cyan-200">
              vault lock: {locked.toFixed(0)} GEN
            </span>
            {bond > 0 && (
              <span className="rounded bg-amber-500/10 px-2 py-1 font-mono text-amber-200 ring-1 ring-amber-400/30">
                appeal bond: {bond} GEN
              </span>
            )}
          </div>
        </div>

        <div className="flex flex-col justify-between rounded-2xl bg-white/[0.03] p-4 ring-1 ring-white/10">
          <div className="text-[11px] text-slate-400">
            {step < 3
              ? "Employer surplus recovery: BLOCKED until every tranche is final."
              : step === 3
                ? branch === "appeal"
                  ? "Appeal pending: the full liability and bond stay locked."
                  : "Both signatures recorded: settlement can execute immediately."
                : "Settlement complete: the receipt is immutable."}
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {step === 2 && (
              <>
                <button
                  onClick={() => {
                    sound.click();
                    setBranch("appeal");
                    setStep(3);
                  }}
                  className="flex items-center gap-1.5 rounded-xl bg-amber-500/15 px-2.5 py-2 text-[11px] font-bold text-amber-100 ring-1 ring-amber-400/30 transition hover:bg-amber-500/25"
                >
                  <Gavel size={13} /> Appeal
                </button>
                <button
                  onClick={() => {
                    sound.click();
                    setBranch("cosign");
                    setStep(3);
                  }}
                  className="flex items-center gap-1.5 rounded-xl bg-cyan-500/15 px-2.5 py-2 text-[11px] font-bold text-cyan-100 ring-1 ring-cyan-400/30 transition hover:bg-cyan-500/25"
                >
                  <Handshake size={13} /> Co-sign
                </button>
              </>
            )}
            <button
              onClick={advance}
              disabled={step >= STEPS.length - 1}
              className="flex items-center gap-1.5 rounded-xl bg-violet-500/20 px-2.5 py-2 text-[11px] font-bold text-violet-100 ring-1 ring-violet-400/30 transition hover:bg-violet-500/30 disabled:opacity-40"
            >
              Advance <ChevronRight size={13} />
            </button>
            <button
              onClick={() => {
                sound.click();
                if (playing) {
                  setPlaying(false);
                } else {
                  if (step === STEPS.length - 1) setStep(0);
                  setPlaying(true);
                }
              }}
              className="flex items-center gap-1.5 rounded-xl bg-white/5 px-2.5 py-2 text-[11px] font-bold text-slate-200 ring-1 ring-white/10 transition hover:bg-white/10"
            >
              <Play size={12} /> {playing ? "Pause" : "Play"}
            </button>
            <button
              onClick={reset}
              className="flex items-center gap-1.5 rounded-xl bg-white/5 px-2.5 py-2 text-[11px] font-bold text-slate-300 ring-1 ring-white/10 transition hover:bg-white/10"
            >
              <RotateCcw size={12} /> Reset
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
