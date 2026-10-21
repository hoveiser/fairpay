import { useMemo, useState } from "react";
import confetti from "canvas-confetti";
import {
  ArrowDownToLine,
  Calculator,
  CheckCircle2,
  Lock,
  Sparkles,
  Unlock,
  Users,
} from "lucide-react";
import {
  ANCHORS,
  BAND_COLOR,
  BAND_LABEL,
  fmt,
  simulate,
  type Anchor,
} from "../lib/fairpay";
import { sound } from "../lib/sound";
import type { Role } from "../lib/wallet";

interface Props {
  role: Role;
}

function Slider({
  label,
  value,
  min,
  max,
  step,
  suffix,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  suffix: string;
  onChange: (value: number) => void;
}) {
  return (
    <label className="block">
      <div className="mb-1.5 flex items-baseline justify-between">
        <span className="text-xs font-semibold text-slate-300">{label}</span>
        <span className="font-mono text-xs text-violet-200">
          {fmt(value)} {suffix}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        className="range w-full"
      />
    </label>
  );
}

export default function PayrollSimulator({ role }: Props) {
  const [base, setBase] = useState(60);
  const [bonus, setBonus] = useState(20);
  const [bond, setBond] = useState(2);
  const [anchor, setAnchor] = useState<Anchor>(80);
  const [windowOpen, setWindowOpen] = useState(true);
  const [settled, setSettled] = useState(false);

  const result = useMemo(
    () => simulate(base, bonus, anchor, windowOpen),
    [base, bonus, anchor, windowOpen],
  );

  function settle() {
    if (result.payout <= 0) {
      sound.error();
      setSettled(false);
      return;
    }
    sound.settle();
    confetti({
      particleCount: 110,
      spread: 72,
      startVelocity: 38,
      origin: { x: 0.72, y: 0.62 },
      colors: ["#a78bfa", "#22d3ee", "#34d399", "#fbbf24"],
      disableForReducedMotion: true,
    });
    setSettled(true);
    window.setTimeout(() => setSettled(false), 3200);
  }

  return (
    <div className="rounded-3xl bg-white/[0.03] p-5 ring-1 ring-white/10 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Calculator size={18} className="text-violet-300" />
            <h3 className="text-base font-bold text-white">What-if payroll simulator</h3>
          </div>
          <p className="mt-1 max-w-2xl text-xs leading-relaxed text-slate-400">
            Move the terms and the consensus anchor. The band, the lock, and the exact
            worker and employer split use the same integer rules as the contract.
          </p>
        </div>
        <span className="rounded-full bg-violet-500/10 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-violet-200 ring-1 ring-violet-400/30">
          PAPITO max liability
        </span>
      </div>

      <div className="mt-5 grid gap-6 lg:grid-cols-[1.05fr_1fr]">
        <div className="space-y-4">
          <Slider label="Base pay" value={base} min={10} max={120} step={1} suffix="GEN" onChange={setBase} />
          <Slider label="Overtime and bonus cap" value={bonus} min={0} max={60} step={1} suffix="GEN" onChange={setBonus} />
          <Slider label="Worker appeal bond" value={bond} min={0} max={10} step={0.5} suffix="GEN" onChange={setBond} />

          <div>
            <div className="mb-2 flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-300">Consensus anchor</span>
              <span className="text-[11px] text-slate-500">discrete ladder only</span>
            </div>
            <div className="grid grid-cols-4 gap-2">
              {ANCHORS.map((value) => (
                <button
                  key={value}
                  onClick={() => {
                    sound.click();
                    setAnchor(value);
                  }}
                  className={
                    "rounded-xl px-2 py-2.5 text-center ring-1 transition " +
                    (anchor === value
                      ? "bg-violet-500/25 ring-violet-400/50"
                      : "bg-white/[0.03] ring-white/10 hover:bg-white/[0.06]")
                  }
                >
                  <div className="font-mono text-lg font-bold text-white">{value}</div>
                  <div className="text-[10px] uppercase tracking-wide text-slate-400">
                    {value === 0 ? "none" : value === 50 ? "partial" : value === 80 ? "standard" : "full"}
                  </div>
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center justify-between rounded-2xl bg-white/[0.03] p-3 ring-1 ring-white/10">
            <div className="flex items-center gap-2 text-xs text-slate-300">
              {windowOpen ? <Lock size={14} className="text-amber-300" /> : <Unlock size={14} className="text-emerald-300" />}
              Appeal window {windowOpen ? "open" : "closed"}
            </div>
            <button
              onClick={() => {
                sound.click();
                setWindowOpen((value) => !value);
              }}
              className={
                "rounded-lg px-2.5 py-1 text-[11px] font-bold ring-1 transition " +
                (windowOpen
                  ? "bg-amber-500/15 text-amber-200 ring-amber-400/30"
                  : "bg-emerald-500/15 text-emerald-200 ring-emerald-400/30")
              }
            >
              {windowOpen ? "Show finality" : "Show window"}
            </button>
          </div>
        </div>

        <div className="rounded-2xl bg-[#0a1020] p-4 ring-1 ring-white/10">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
              Settlement preview
            </span>
            <span className={"rounded-full px-2 py-0.5 text-[10px] font-bold ring-1 " + BAND_COLOR[result.band]}>
              {result.band}
            </span>
          </div>

          <div className="mt-4 grid grid-cols-2 gap-3">
            <div>
              <div className="text-[11px] text-slate-500">Worker payout</div>
              <div className="font-mono text-2xl font-bold text-white">{fmt(result.payout)}</div>
              <div className="text-[10px] text-slate-500">GEN</div>
            </div>
            <div className="text-right">
              <div className="text-[11px] text-slate-500">Employer refund</div>
              <div className="font-mono text-2xl font-bold text-slate-200">{fmt(result.refund)}</div>
              <div className="text-[10px] text-slate-500">GEN</div>
            </div>
          </div>

          <div className="mt-4">
            <div className="mb-1.5 flex items-center justify-between text-[11px]">
              <span className="text-slate-400">
                {result.windowOpen ? "Vault lock: 100% of max liability" : "Vault lock: exact payout"}
              </span>
              <span className="font-mono text-slate-300">{fmt(result.locked)} GEN</span>
            </div>
            <div className="h-2.5 overflow-hidden rounded-full bg-white/5">
              <div
                className={
                  "h-full rounded-full transition-all duration-500 " +
                  (result.windowOpen
                    ? "bg-gradient-to-r from-violet-500 to-amber-400"
                    : "bg-gradient-to-r from-emerald-500 to-cyan-400")
                }
                style={{ width: result.lockPct + "%" }}
              />
            </div>
            <div className="mt-1 text-[10px] text-slate-500">
              Max liability {fmt(result.maxLiability)} GEN
              {windowOpen ? " - appeal window still live" : " - every tranche final"}
            </div>
          </div>

          <div className="mt-4">
            <div className="mb-1.5 text-[11px] text-slate-400">Settlement split</div>
            <div className="flex h-2.5 overflow-hidden rounded-full bg-white/5">
              <div
                className="h-full bg-gradient-to-r from-violet-500 to-fuchsia-400 transition-all duration-500"
                style={{ width: (result.payout / Math.max(1, result.maxLiability)) * 100 + "%" }}
              />
              <div
                className="h-full bg-slate-600/70 transition-all duration-500"
                style={{ width: (result.refund / Math.max(1, result.maxLiability)) * 100 + "%" }}
              />
            </div>
            <div className="mt-1 flex justify-between text-[10px] text-slate-500">
              <span>worker {fmt(result.payout)}</span>
              <span>employer {fmt(result.refund)}</span>
            </div>
          </div>

          <div className="mt-4 flex items-center gap-2 rounded-xl bg-white/[0.03] p-2.5 text-[11px] text-slate-400 ring-1 ring-white/10">
            <Users size={13} className="text-cyan-300" />
            Appeal bond {fmt(bond)} GEN stays in the vault while an appeal is pending.
          </div>

          <button
            onClick={settle}
            className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-violet-500/25 px-3 py-2.5 text-xs font-bold text-violet-100 ring-1 ring-violet-400/40 transition hover:bg-violet-500/35"
          >
            <Sparkles size={14} />
            Simulate settlement
          </button>

          {settled && (
            <div className="mt-3 rounded-xl bg-emerald-500/10 p-3 text-[11px] text-emerald-100 ring-1 ring-emerald-400/30">
              <div className="flex items-center gap-1.5 font-bold">
                <CheckCircle2 size={13} />
                Settlement receipt (simulated)
              </div>
              <div className="mt-1 font-mono text-emerald-200/80">
                payout {fmt(result.payout)} + refund {fmt(result.refund)} ={" "}
                {fmt(result.maxLiability)} GEN
              </div>
              <div className="mt-1 flex items-center gap-1 text-emerald-200/60">
                <ArrowDownToLine size={11} />
                {BAND_LABEL[result.band]}
              </div>
            </div>
          )}

          <p className="mt-3 text-[10px] leading-relaxed text-slate-500">
            {role === "EMPLOYER"
              ? "As employer you fund the full max liability and can only recover unearned surplus after the window closes and every appeal is resolved."
              : "As worker the full max liability is protected while the window is open; your appeal bond is refunded only if the appeal improves the verified payout."}
          </p>
        </div>
      </div>
    </div>
  );
}
