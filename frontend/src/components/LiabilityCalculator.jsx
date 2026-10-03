import React, { useMemo, useState } from "react";
import {
  maxLiabilityAtto,
  payoutAtto,
  formatGen,
  attoToGen,
  TIERS,
  TIER_MULTIPLIER,
} from "../liability.mjs";

function Bar({ label, atto, maxAtto, color, note }) {
  const pct = maxAtto > 0n ? Math.min(100, (Number((atto * 10000n) / maxAtto)) / 100) : 0;
  return (
    <div>
      <div className="mb-1 flex items-baseline justify-between">
        <span className="text-sm font-medium text-slate-200">{label}</span>
        <span className="font-mono text-sm text-white">{formatGen(atto)} GEN</span>
      </div>
      <div className="h-7 w-full overflow-hidden rounded-lg bg-black/40 ring-1 ring-white/5">
        <div
          className={"bar-track flex h-full items-center justify-end rounded-lg pr-2 " + color}
          style={{ width: pct + "%" }}
          data-testid={label.toLowerCase().includes("reserved") ? "bar-reserved" : "bar-payout"}
          data-width={pct.toFixed(1)}
        >
          {pct > 12 && <span className="text-[10px] font-bold text-black/70">{note}</span>}
        </div>
      </div>
    </div>
  );
}

export default function LiabilityCalculator() {
  const [hours, setHours] = useState(10);
  const [rate, setRate] = useState(1);
  const [tier, setTier] = useState("MEDIUM");

  const reserved = useMemo(() => maxLiabilityAtto(hours, rate), [hours, rate]);
  const payout = useMemo(() => payoutAtto(hours, rate, tier), [hours, rate, tier]);
  const maxAtto = reserved > payout ? reserved : payout === 0n ? 1n : payout;
  const headroom = reserved - payout;

  return (
    <section className="glass rounded-2xl p-6 shadow-xl">
      <h2 className="text-lg font-bold tracking-tight text-white">2. Reserved-Liability Calculator</h2>
      <p className="mt-1 text-sm text-slate-400">
        The employer escrow always reserves <code className="text-amber-300">hours x rate x 1.25</code>, rounded up, so
        <code className="text-amber-300"> recover_budget</code> can never defund a live appeal window that could still
        pay the HIGH tier.
      </p>

      <div className="mt-5 grid gap-5 sm:grid-cols-2">
        <label className="block">
          <div className="mb-1 flex justify-between text-sm">
            <span className="text-slate-300">Hours claimed</span>
            <span className="font-mono text-white" data-testid="hours-value">{hours}</span>
          </div>
          <input
            id="hours"
            data-testid="hours"
            type="range"
            min="0"
            max="40"
            value={hours}
            onChange={(e) => setHours(Number(e.target.value))}
            className="w-full"
          />
        </label>
        <label className="block">
          <div className="mb-1 flex justify-between text-sm">
            <span className="text-slate-300">Rate (GEN / hour)</span>
            <span className="font-mono text-white" data-testid="rate-value">{rate}</span>
          </div>
          <input
            id="rate"
            data-testid="rate"
            type="range"
            min="1"
            max="20"
            value={rate}
            onChange={(e) => setRate(Number(e.target.value))}
            className="w-full"
          />
        </label>
      </div>

      <div className="mt-4">
        <div className="mb-2 text-sm text-slate-300">Settled AI tier</div>
        <div className="flex flex-wrap gap-2">
          {TIERS.map((t) => (
            <button
              key={t}
              data-tier={t}
              onClick={() => setTier(t)}
              className={
                "rounded-lg px-3 py-1.5 text-xs font-semibold ring-1 transition " +
                (t === tier
                  ? "bg-gradient-to-r from-gl-orange to-gl-violet text-black ring-transparent"
                  : "bg-white/5 text-slate-300 ring-white/10 hover:brightness-125")
              }
            >
              {t} <span className="opacity-70">x{TIER_MULTIPLIER[t] / 100}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="mt-6 space-y-4">
        <Bar
          label="Max Reachable Payout (Reserved)"
          atto={reserved}
          maxAtto={maxAtto}
          color="bg-gradient-to-r from-gl-orange to-gl-amber"
          note={`${formatGen(reserved)} GEN`}
        />
        <Bar
          label="Actual Payout (settled tier)"
          atto={payout}
          maxAtto={maxAtto}
          color="bg-gradient-to-r from-gl-violet to-purple-400"
          note={`${formatGen(payout)} GEN`}
        />
      </div>

      <div className="mt-4 rounded-xl bg-black/30 p-3 text-sm ring-1 ring-white/5" data-testid="reserve-note">
        <span className="text-slate-400">Protected headroom (reserved minus settled payout): </span>
        <span className="font-mono font-semibold text-emerald-300">{formatGen(headroom)} GEN</span>
        <span className="ml-2 text-xs text-slate-500">
          ({attoToGen(reserved).toFixed(2)} vs {attoToGen(payout).toFixed(2)} GEN) stays locked until the appeal window
          closes or the period settles.
        </span>
      </div>
    </section>
  );
}
