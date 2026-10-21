import { useState, type ReactNode } from "react";
import {
  AlertTriangle,
  ExternalLink,
  Handshake,
  LockKeyhole,
  ShieldAlert,
  Terminal,
  CheckCircle2,
} from "lucide-react";
import {
  guardPostSettlement,
  guardPrematureSurplus,
  guardSingleParty,
  type GuardResult,
} from "../lib/fairpay";
import { sound } from "../lib/sound";

type GuardId = "premature" | "cosign" | "postsettle";

const GUARDS: { id: GuardId; label: string; hint: string; icon: ReactNode }[] = [
  {
    id: "premature",
    label: "Premature surplus clawback",
    hint: "Employer tries to recover surplus while the appeal window is open.",
    icon: <LockKeyhole size={15} />,
  },
  {
    id: "cosign",
    label: "Single-party co-sign",
    hint: "Only one party signs the settlement proposal.",
    icon: <Handshake size={15} />,
  },
  {
    id: "postsettle",
    label: "Post-settlement mutation",
    hint: "A new proposal is sent after the agreement is settled.",
    icon: <ShieldAlert size={15} />,
  },
];

export default function GuardLab() {
  const [running, setRunning] = useState<GuardId | null>(null);
  const [output, setOutput] = useState<GuardResult | null>(null);

  function run(id: GuardId) {
    sound.click();
    setRunning(id);
    setOutput(null);
    window.setTimeout(() => {
      const result =
        id === "premature"
          ? guardPrematureSurplus(true, false)
          : id === "cosign"
            ? guardSingleParty(1)
            : guardPostSettlement(true);
      setOutput(result);
      setRunning(null);
      if (result.outcome === "REVERT") sound.error();
      else if (result.outcome === "NO_SETTLEMENT") sound.click();
      else sound.success();
    }, 520);
  }

  const tone =
    output?.outcome === "REVERT"
      ? "text-rose-300 bg-rose-500/10 ring-rose-400/30"
      : output?.outcome === "NO_SETTLEMENT"
        ? "text-amber-200 bg-amber-500/10 ring-amber-400/30"
        : "text-emerald-200 bg-emerald-500/10 ring-emerald-400/30";

  return (
    <div className="rounded-3xl bg-white/[0.03] p-5 ring-1 ring-white/10 sm:p-6">
      <div className="flex items-start gap-2">
        <Terminal size={18} className="mt-0.5 text-rose-300" />
        <div>
          <h3 className="text-base font-bold text-white">Security guard lab</h3>
          <p className="mt-1 max-w-xl text-xs leading-relaxed text-slate-400">
            One-click replay of the deployed guards. Each result mirrors the exact
            deterministic check in the contract; the real on-chain reverts are linked below.
          </p>
        </div>
      </div>

      <div className="mt-4 grid gap-2">
        {GUARDS.map((guard) => (
          <button
            key={guard.id}
            onClick={() => run(guard.id)}
            disabled={running !== null}
            className="group flex items-start gap-3 rounded-xl bg-white/[0.03] p-3 text-left ring-1 ring-white/10 transition hover:bg-white/[0.06] disabled:opacity-60"
          >
            <span className="mt-0.5 rounded-lg bg-white/5 p-1.5 text-slate-300 ring-1 ring-white/10">
              {guard.icon}
            </span>
            <span className="min-w-0 flex-1">
              <span className="block text-xs font-bold text-slate-100">{guard.label}</span>
              <span className="mt-0.5 block text-[11px] leading-relaxed text-slate-500">
                {guard.hint}
              </span>
            </span>
            <span className="mt-0.5 text-[10px] font-bold uppercase tracking-wider text-violet-300 opacity-0 transition group-hover:opacity-100">
              {running === guard.id ? "running" : "run"}
            </span>
          </button>
        ))}
      </div>

      <div className="mt-4 rounded-xl bg-[#060a12] p-3 ring-1 ring-white/10">
        <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-wider text-slate-500">
          <Terminal size={12} /> guard output
        </div>
        {output ? (
          <div className="mt-2 space-y-1.5">
            <div className="font-mono text-[11px] text-slate-500">
              $ fairpay guard {output.id}
            </div>
            <div className="flex items-center gap-2">
              <span className={"rounded px-2 py-0.5 text-[10px] font-bold ring-1 " + tone}>
                {output.outcome}
              </span>
              <span className="text-[11px] font-semibold text-slate-200">{output.message}</span>
            </div>
            <p className="text-[11px] leading-relaxed text-slate-500">{output.detail}</p>
            {output.outcome === "REVERT" && (
              <div className="flex items-start gap-1.5 text-[10px] text-rose-300/80">
                <AlertTriangle size={11} className="mt-0.5 shrink-0" />
                The transaction reverts, so no state change and no funds move.
              </div>
            )}
            {output.outcome === "NO_SETTLEMENT" && (
              <div className="flex items-start gap-1.5 text-[10px] text-amber-200/80">
                <CheckCircle2 size={11} className="mt-0.5 shrink-0" />
                The proposal is stored, but the vault balance is unchanged.
              </div>
            )}
          </div>
        ) : (
          <div className="mt-2 font-mono text-[11px] text-slate-600">
            select a guard to run the deterministic replay
          </div>
        )}
      </div>

      <a
        href="https://github.com/hoveiser/fairpay/blob/main/docs/evidence.md"
        target="_blank"
        rel="noreferrer"
        className="mt-3 flex items-center gap-1.5 text-[11px] font-semibold text-cyan-300 transition hover:text-cyan-200"
      >
        Live guard reverts and tx hashes in docs/evidence.md <ExternalLink size={11} />
      </a>
    </div>
  );
}
