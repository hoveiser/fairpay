import React from "react";
import GatewayValidator from "./components/GatewayValidator.jsx";
import LiabilityCalculator from "./components/LiabilityCalculator.jsx";
import LiveStatus from "./components/LiveStatus.jsx";
import { CONTRACT_ADDRESS } from "./rpc.mjs";

const REPO = "https://github.com/hoveiser/fairpay";
const EXPLORER = `https://explorer-studio.genlayer.com/address/${CONTRACT_ADDRESS}`;

export default function App() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:py-12">
      <header className="mb-8">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="grid h-11 w-11 place-items-center rounded-xl bg-gradient-to-br from-gl-orange to-gl-violet text-lg font-black text-black shadow-lg">
              F
            </div>
            <div>
              <h1 className="text-2xl font-extrabold tracking-tight text-white">
                FairPay
                <span className="ml-2 rounded-md bg-gl-violet/20 px-2 py-0.5 align-middle text-xs font-bold text-purple-200 ring-1 ring-purple-400/30">
                  v0.4.1
                </span>
              </h1>
              <p className="text-sm text-slate-400">AI-audited payroll on GenLayer StudioNet</p>
            </div>
          </div>
          <nav className="flex items-center gap-2 text-sm">
            <a href={REPO} target="_blank" rel="noreferrer" className="rounded-lg bg-white/5 px-3 py-1.5 text-slate-200 ring-1 ring-white/10 hover:brightness-125">
              Repository
            </a>
            <a href={EXPLORER} target="_blank" rel="noreferrer" className="rounded-lg bg-white/5 px-3 py-1.5 text-slate-200 ring-1 ring-white/10 hover:brightness-125">
              Explorer
            </a>
          </nav>
        </div>
        <p className="mt-4 max-w-3xl text-sm leading-relaxed text-slate-400">
          An interactive explorer for the two v0.4.x fixes. The gateway validator replays the exact on-chain URL gate,
          the calculator shows how reserved liability protects the escrow, and the status panel reads the live deployed
          contract over GenLayer JSON-RPC. Every number here is computed the same way the contract computes it.
        </p>
      </header>

      <main className="grid gap-6">
        <GatewayValidator />
        <LiabilityCalculator />
        <LiveStatus />
      </main>

      <footer className="mt-10 border-t border-white/5 pt-5 text-xs text-slate-500">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span>
            Contract <code className="font-mono text-slate-400">{CONTRACT_ADDRESS}</code> on StudioNet (chain id 61999)
          </span>
          <span>Runner pinned <code className="font-mono text-slate-400">py-genlayer:1jb45aa...</code> - source byte-matched on chain</span>
        </div>
      </footer>
    </div>
  );
}
