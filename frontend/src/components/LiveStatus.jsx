import React, { useCallback, useEffect, useState } from "react";
import { readLiveState, CONTRACT_ADDRESS, EXPLORER_URL, RPC_URL } from "../rpc.mjs";
import { formatGen } from "../liability.mjs";

function Stat({ label, value, sub, accent }) {
  return (
    <div className="rounded-xl bg-black/30 p-4 ring-1 ring-white/5">
      <div className="text-xs uppercase tracking-wide text-slate-400">{label}</div>
      <div className={"mt-1 font-mono text-2xl font-bold " + (accent || "text-white")} data-testid={"stat-" + label.toLowerCase().replace(/[^a-z]+/g, "-")}>
        {value}
      </div>
      {sub && <div className="mt-0.5 text-xs text-slate-500">{sub}</div>}
    </div>
  );
}

export default function LiveStatus() {
  const [jobId, setJobId] = useState(3);
  const [state, setState] = useState(null);
  const [status, setStatus] = useState("idle"); // idle | loading | ok | error
  const [error, setError] = useState("");

  const load = useCallback(async (id) => {
    setStatus("loading");
    setError("");
    try {
      const s = await readLiveState(id);
      setState(s);
      setStatus("ok");
    } catch (e) {
      setError(String(e && e.message ? e.message : e));
      setStatus("error");
    }
  }, []);

  useEffect(() => {
    load(jobId);
  }, [jobId, load]);

  const job = state && state.job;

  return (
    <section className="glass rounded-2xl p-6 shadow-xl">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold tracking-tight text-white">3. Live StudioNet Contract State</h2>
          <p className="mt-1 text-sm text-slate-400">
            Read directly from the deployed contract over JSON-RPC <code className="text-amber-300">gen_call</code>, then
            decoded in-browser with the same genbase codec the SDK uses.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-sm text-slate-300">Job&nbsp;#</label>
          <input
            id="job-id"
            data-testid="job-id"
            type="number"
            min="1"
            value={jobId}
            onChange={(e) => setJobId(Math.max(1, Number(e.target.value) || 1))}
            className="w-20 rounded-lg border border-white/10 bg-black/40 px-3 py-1.5 font-mono text-sm outline-none focus:ring-2 focus:ring-gl-violet/50"
          />
          <button
            id="refresh-live"
            data-testid="refresh-live"
            onClick={() => load(jobId)}
            className="rounded-lg bg-gradient-to-r from-gl-orange to-gl-violet px-4 py-1.5 text-sm font-semibold text-black transition hover:brightness-110"
          >
            {status === "loading" ? "Reading..." : "Refresh"}
          </button>
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
        <span className="rounded-full bg-emerald-500/10 px-3 py-1 font-mono text-emerald-300 ring-1 ring-emerald-500/30">
          {status === "ok" ? "live on-chain read" : status === "loading" ? "querying RPC..." : status === "error" ? "RPC error" : "idle"}
        </span>
        <a className="text-slate-400 underline decoration-dotted hover:text-white" href={`${EXPLORER_URL}/address/${CONTRACT_ADDRESS}`} target="_blank" rel="noreferrer">
          {CONTRACT_ADDRESS}
        </a>
        <span className="text-slate-600">{RPC_URL}</span>
      </div>

      {status === "error" && (
        <div className="mt-4 rounded-xl bg-rose-500/10 p-4 text-sm text-rose-200 ring-1 ring-rose-500/30">
          {error}
        </div>
      )}

      {state && status !== "error" && (
        <>
          <div className="mt-5 grid gap-3 sm:grid-cols-3">
            <Stat label="Contract escrow balance" value={`${formatGen(state.contractBalanceAtto)} GEN`} sub="contract_balance() across all jobs" accent="text-amber-300" />
            <Stat label={`Job #${state.jobId} budget`} value={`${formatGen(state.jobBudgetAtto)} GEN`} sub="remaining locked in this job" accent="text-purple-300" />
            <Stat label={`Job #${state.jobId} reserved liability`} value={`${formatGen(state.reservedAtto)} GEN`} sub="max reachable payout still protected" accent="text-emerald-300" />
          </div>

          {job && (
            <dl className="mt-4 grid grid-cols-2 gap-x-6 gap-y-2 rounded-xl bg-black/20 p-4 text-sm sm:grid-cols-3">
              {[
                ["Employer", job.employer],
                ["Worker", job.worker],
                ["Role", job.role],
                ["Rate (GEN/hr)", job.rate],
                ["Appeal window (s)", job.appeal_window_sec],
                ["Max hrs / period", job.max_hours_per_period],
                ["Open period", job.open_period],
                ["Periods", (job.period_ids || []).length],
              ].map(([k, v]) => (
                <div key={k} className="flex flex-col">
                  <dt className="text-xs uppercase tracking-wide text-slate-500">{k}</dt>
                  <dd className="truncate font-mono text-slate-200" title={String(v)}>{String(v)}</dd>
                </div>
              ))}
            </dl>
          )}
        </>
      )}
    </section>
  );
}
