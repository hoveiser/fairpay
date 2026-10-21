import { useCallback, useEffect, useState, type ReactNode } from "react";
import {
  Activity,
  CheckCircle2,
  ExternalLink,
  RefreshCw,
  ShieldCheck,
  Vault,
  XCircle,
} from "lucide-react";
import {
  CONTRACT_ADDRESS,
  CONTRACT_READY,
  loadLiveState,
  type LiveState,
} from "../lib/rpc";
import { BAND_LABEL, fmt, type Band } from "../lib/fairpay";
import { shortAddress } from "../lib/wallet";
import { sound } from "../lib/sound";

const ATTO = 1e18;
const EXPLORER = "https://explorer-studio.genlayer.com/address/" + CONTRACT_ADDRESS;

function gen(value?: string | number | null): number {
  if (value === undefined || value === null || value === "") return 0;
  return Number(value) / ATTO;
}

function Stat({
  icon,
  label,
  value,
  hint,
}: {
  icon: ReactNode;
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div className="rounded-2xl bg-white/[0.03] p-4 ring-1 ring-white/10">
      <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
        {icon}
        {label}
      </div>
      <div className="mt-2 font-mono text-xl font-bold text-white">{value}</div>
      {hint && <div className="mt-1 text-[11px] text-slate-500">{hint}</div>}
    </div>
  );
}

export default function LiveContract() {
  const [data, setData] = useState<LiveState | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    if (!CONTRACT_READY) return;
    setLoading(true);
    setError("");
    try {
      const next = await loadLiveState();
      setData(next);
      sound.success();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Live read failed.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (!CONTRACT_READY) {
    return (
      <div className="rounded-3xl border border-dashed border-white/15 bg-white/[0.02] p-6">
        <div className="flex items-center gap-3">
          <Vault size={20} className="text-violet-300" />
          <h3 className="text-sm font-bold text-white">Milestone v1 deployment pending</h3>
        </div>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-400">
          The frontend is built before the final contract address is recorded. After
          <code className="mx-1 rounded bg-white/5 px-1.5 py-0.5 font-mono text-[11px] text-violet-200">
            scripts/deploy_studionet.py
          </code>
          completes, the address is written into this page and the four live reads below
          show real StudioNet state.
        </p>
      </div>
    );
  }

  const vault = data?.vault;
  const agreement = data?.agreement;
  const tranche = data?.tranche;
  const invariantOk = Boolean(data?.invariant && vault?.invariant_holds);
  const band = (tranche?.payroll_band || "") as Band;
  const bandText = BAND_LABEL[band] || "No audit result yet";

  return (
    <div className="rounded-3xl bg-white/[0.03] p-5 ring-1 ring-white/10 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Activity size={18} className="text-cyan-300" />
            <h3 className="text-base font-bold text-white">Live contract reads</h3>
            <span className="rounded-full bg-cyan-500/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-cyan-200 ring-1 ring-cyan-400/30">
              StudioNet 61999
            </span>
          </div>
          <p className="mt-1 text-xs text-slate-400">
            {shortAddress(CONTRACT_ADDRESS)} - four to five gen_call reads on load, no polling.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <a
            href={EXPLORER}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1.5 rounded-xl bg-white/5 px-3 py-2 text-xs font-semibold text-slate-200 ring-1 ring-white/10 transition hover:bg-white/10"
          >
            Explorer <ExternalLink size={12} />
          </a>
          <button
            onClick={() => {
              sound.click();
              void load();
            }}
            disabled={loading}
            className="flex items-center gap-1.5 rounded-xl bg-violet-500/20 px-3 py-2 text-xs font-bold text-violet-100 ring-1 ring-violet-400/30 transition hover:bg-violet-500/30 disabled:opacity-50"
          >
            <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="mt-4 flex items-start gap-2 rounded-2xl bg-rose-500/10 p-3 text-xs text-rose-200 ring-1 ring-rose-400/30">
          <XCircle size={14} className="mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {!data && loading && (
        <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="h-24 animate-pulse rounded-2xl bg-white/[0.04]" />
          ))}
        </div>
      )}

      {vault && (
        <>
          <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Stat
              icon={<Vault size={13} />}
              label="Vault custody"
              value={fmt(gen(vault.vault_custody_balance)) + " GEN"}
              hint="FPT held for payroll and bonds"
            />
            <Stat
              icon={<ShieldCheck size={13} />}
              label="Locked payroll"
              value={fmt(gen(vault.locked_payroll_escrows)) + " GEN"}
              hint="PAPITO max liability"
            />
            <Stat
              icon={<Activity size={13} />}
              label="Appeal bonds"
              value={fmt(gen(vault.active_appeal_bonds)) + " GEN"}
              hint="Held while an appeal is live"
            />
            <div
              className={
                "rounded-2xl p-4 ring-1 " +
                (invariantOk
                  ? "bg-emerald-500/10 ring-emerald-400/30"
                  : "bg-rose-500/10 ring-rose-400/30")
              }
            >
              <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wider">
                {invariantOk ? (
                  <CheckCircle2 size={13} className="text-emerald-300" />
                ) : (
                  <XCircle size={13} className="text-rose-300" />
                )}
                <span className={invariantOk ? "text-emerald-200" : "text-rose-200"}>
                  Vault invariant
                </span>
              </div>
              <div
                className={
                  "mt-2 font-mono text-xl font-bold " +
                  (invariantOk ? "text-emerald-100" : "text-rose-100")
                }
              >
                {invariantOk ? "HOLDS" : "BROKEN"}
              </div>
              <div className="mt-1 text-[11px] text-slate-400">
                vault == locked + bonds
              </div>
            </div>
          </div>

          {agreement ? (
            <div className="mt-4 grid gap-3 lg:grid-cols-[1.2fr_1fr]">
              <div className="rounded-2xl bg-white/[0.03] p-4 ring-1 ring-white/10">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                    Latest agreement
                  </span>
                  <span className="rounded-full bg-violet-500/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-violet-200 ring-1 ring-violet-400/30">
                    #{agreement.id} {agreement.status}
                  </span>
                </div>
                <div className="mt-3 grid grid-cols-2 gap-3 text-xs">
                  <div>
                    <div className="text-slate-500">Max liability</div>
                    <div className="font-mono text-sm text-white">
                      {fmt(gen(agreement.max_liability))} GEN
                    </div>
                  </div>
                  <div>
                    <div className="text-slate-500">Currently locked</div>
                    <div className="font-mono text-sm text-white">
                      {fmt(gen(agreement.locked_amount))} GEN
                    </div>
                  </div>
                  <div>
                    <div className="text-slate-500">Tranches</div>
                    <div className="font-mono text-sm text-white">
                      {agreement.tranche_indexes.length} / {agreement.tranche_count}
                    </div>
                  </div>
                  <div>
                    <div className="text-slate-500">Appeal window</div>
                    <div className="font-mono text-sm text-white">
                      {Math.round(agreement.appeal_window_sec / 3600)}h
                    </div>
                  </div>
                </div>
              </div>

              <div className="rounded-2xl bg-white/[0.03] p-4 ring-1 ring-white/10">
                <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                  Tranche 0 consensus
                </div>
                {tranche && tranche.payroll_band ? (
                  <>
                    <div className="mt-3 text-sm font-bold text-white">{bandText}</div>
                    <div className="mt-2 flex flex-wrap gap-2 text-[11px]">
                      <span className="rounded bg-white/5 px-2 py-1 font-mono text-cyan-200">
                        anchor {tranche.delivery_anchor}
                      </span>
                      <span className="rounded bg-white/5 px-2 py-1 font-mono text-slate-300">
                        {tranche.evidence_authenticated ? "authenticated" : "unauthenticated"}
                      </span>
                      <span className="rounded bg-white/5 px-2 py-1 font-mono text-emerald-200">
                        {fmt(gen(tranche.worker_payout))} GEN payout
                      </span>
                    </div>
                    <div className="mt-2 text-[11px] text-slate-500">
                      Tranche status: {tranche.status}
                      {tranche.bond_outcome !== "none" ? " - bond " + tranche.bond_outcome : ""}
                    </div>
                  </>
                ) : (
                  <div className="mt-3 text-xs text-slate-400">
                    No audit result stored yet for the latest agreement.
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="mt-4 rounded-2xl bg-white/[0.03] p-4 text-xs text-slate-400 ring-1 ring-white/10">
              No agreements have been created on this deployment yet.
            </div>
          )}
        </>
      )}
    </div>
  );
}
