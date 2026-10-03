import React, { useMemo, useState } from "react";
import { explain, isContentAddressedUrl, GATEWAY_HOSTS } from "../validateUrl.mjs";

const PRESETS = [
  { label: "Valid (ipfs.io)", url: "https://ipfs.io/ipfs/bafkreidwkl2tdyhpeij4es7ng23qiexzxn5nq2ae2ckf6nmtsahrsit5zq", kind: "ok" },
  { label: "Valid (Pinata)", url: "https://gateway.pinata.cloud/ipfs/QmbWqxBEKC3P8tqsKc98xmWNzrzDtRLMiMPL8wBuTGsMnR", kind: "ok" },
  { label: "Lookalike host", url: "https://ipfs.io.evil.com/ipfs/bafkreidwkl2tdyhpeij4es7ng23qiexzxn5nq2ae2ckf6nmtsahrsit5zq", kind: "bad" },
  { label: "Port smuggling", url: "https://ipfs.io:8443/ipfs/bafkreidwkl2tdyhpeij4es7ng23qiexzxn5nq2ae2ckf6nmtsahrsit5zq", kind: "bad" },
  { label: "Not https", url: "http://dweb.link/ipfs/bafkreidwkl2tdyhpeij4es7ng23qiexzxn5nq2ae2ckf6nmtsahrsit5zq", kind: "bad" },
  { label: "Extra path segment", url: "https://w3s.link/ipfs/bafkreidwkl2tdyhpeij4es7ng23qiexzxn5nq2ae2ckf6nmtsahrsit5zq/evil", kind: "bad" },
  { label: "Query + fragment", url: "https://ipfs.io/ipfs/bafkreidwkl2tdyhpeij4es7ng23qiexzxn5nq2ae2ckf6nmtsahrsit5zq?token=1#x", kind: "bad" },
  { label: "Bad CID", url: "https://ipfs.io/ipfs/not-a-valid-cid", kind: "bad" },
];

function StatusPill({ ok }) {
  return (
    <span
      data-testid="verdict-pill"
      className={
        "inline-flex items-center gap-2 rounded-full px-4 py-1.5 text-sm font-semibold ring-1 " +
        (ok
          ? "bg-emerald-500/15 text-emerald-300 ring-emerald-400/40"
          : "bg-rose-500/15 text-rose-300 ring-rose-400/40")
      }
    >
      <span className={"h-2.5 w-2.5 rounded-full " + (ok ? "bg-emerald-400" : "bg-rose-400")} />
      {ok ? "ACCEPTED by contract" : "REVERTED by contract"}
    </span>
  );
}

export default function GatewayValidator() {
  const [url, setUrl] = useState(PRESETS[0].url);
  const report = useMemo(() => explain(url), [url]);
  const accepted = isContentAddressedUrl(url);

  return (
    <section className="glass rounded-2xl p-6 shadow-xl">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold tracking-tight text-white">1. Gateway Validator</h2>
          <p className="mt-1 text-sm text-slate-400">
            Live port of <code className="text-amber-300">_is_content_addressed_url()</code>. Type any URL and watch
            submit_period decide, before a single byte of state changes.
          </p>
        </div>
        <StatusPill ok={accepted} />
      </div>

      <input
        id="gateway-input"
        data-testid="gateway-input"
        spellCheck={false}
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        placeholder="https://ipfs.io/ipfs/<CID>"
        className={
          "w-full rounded-xl border bg-black/40 px-4 py-3 font-mono text-sm outline-none transition focus:ring-2 " +
          (accepted
            ? "border-emerald-500/40 focus:ring-emerald-400/40"
            : "border-rose-500/40 focus:ring-rose-400/40")
        }
      />

      <div className="mt-3 flex flex-wrap gap-2">
        {PRESETS.map((p) => (
          <button
            key={p.label}
            data-preset={p.label}
            onClick={() => setUrl(p.url)}
            className={
              "rounded-lg px-3 py-1.5 text-xs font-medium ring-1 transition hover:brightness-125 " +
              (p.kind === "ok"
                ? "bg-emerald-500/10 text-emerald-200 ring-emerald-500/30"
                : "bg-rose-500/10 text-rose-200 ring-rose-500/30")
            }
          >
            {p.label}
          </button>
        ))}
      </div>

      <div className="mt-3 text-xs text-slate-500">
        Allowlist: {GATEWAY_HOSTS.map((h) => (
          <span key={h} className="mr-2 inline-block rounded bg-purple-500/10 px-2 py-0.5 font-mono text-purple-200 ring-1 ring-purple-500/20">{h}</span>
        ))}
      </div>

      <ul className="mt-5 space-y-1.5" data-testid="validator-steps">
        {report.steps.map((s, i) => (
          <li
            key={i}
            className={
              "flex items-center gap-3 rounded-lg border-l-2 bg-black/20 px-3 py-2 text-sm " +
              (s.pass ? "border-emerald-400/70" : "border-rose-400/70")
            }
          >
            <span className={"font-mono text-xs " + (s.pass ? "text-emerald-400" : "text-rose-400")}>
              {s.pass ? "PASS" : "FAIL"}
            </span>
            <span className="min-w-40 text-slate-200">{s.label}</span>
            <span className={"ml-auto truncate text-right text-xs " + (s.pass ? "text-slate-500" : "text-rose-300")}>
              {s.detail}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
