import { useState, type ReactNode } from "react";
import {
  ArrowUpRight,
  BookOpen,
  Coins,
  FileCheck2,
  Code2,
  Handshake,
  Landmark,
  Play,
  ShieldCheck,
  Sparkles,
  Vault,
} from "lucide-react";
import WalletBar from "./components/WalletBar";
import PayrollSimulator from "./components/PayrollSimulator";
import TimelineStudio from "./components/TimelineStudio";
import ConsensusInspector from "./components/ConsensusInspector";
import GuardLab from "./components/GuardLab";
import LiveContract from "./components/LiveContract";
import { CONTRACT_ADDRESS, CONTRACT_READY } from "./lib/rpc";
import { shortAddress, type Role, type WalletIdentity } from "./lib/wallet";
import { sound } from "./lib/sound";

const REPO = "https://github.com/hoveiser/fairpay";
const EVIDENCE = REPO + "/blob/main/docs/evidence.md";
const EXPLORER = "https://explorer-studio.genlayer.com/address/" + CONTRACT_ADDRESS;
const LOGO = import.meta.env.BASE_URL + "logo.png";
const DEMO = import.meta.env.BASE_URL + "demo-video-subtitled.mp4";

function SectionHeader({
  index,
  icon,
  title,
  subtitle,
}: {
  index: string;
  icon: ReactNode;
  title: string;
  subtitle: string;
}) {
  return (
    <div className="mb-4 flex items-start gap-3">
      <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-white/5 text-[11px] font-bold text-violet-200 ring-1 ring-white/10">
        {index}
      </span>
      <div>
        <div className="flex items-center gap-2">
          {icon}
          <h2 className="text-lg font-bold tracking-tight text-white">{title}</h2>
        </div>
        <p className="mt-0.5 max-w-3xl text-xs leading-relaxed text-slate-400">{subtitle}</p>
      </div>
    </div>
  );
}

function Chip({ icon, children }: { icon: ReactNode; children: ReactNode }) {
  return (
    <span className="flex items-center gap-1.5 rounded-full bg-white/5 px-3 py-1.5 text-[11px] font-semibold text-slate-300 ring-1 ring-white/10">
      {icon}
      {children}
    </span>
  );
}

export default function App() {
  const [role, setRole] = useState<Role>("EMPLOYER");
  const [wallet, setWallet] = useState<WalletIdentity | null>(null);
  const [muted, setMuted] = useState(sound.isMuted());

  function scrollTo(id: string) {
    sound.click();
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  return (
    <div className="relative min-h-screen overflow-hidden">
      <div className="pointer-events-none absolute inset-0 grid-bg opacity-60" />
      <div className="pointer-events-none absolute -left-40 top-[-10rem] h-[34rem] w-[34rem] rounded-full bg-violet-600/20 blur-[120px]" />
      <div className="pointer-events-none absolute -right-40 top-40 h-[30rem] w-[30rem] rounded-full bg-cyan-500/10 blur-[120px]" />

      <header className="relative z-20 border-b border-white/5 bg-[#070b14]/80 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-4 py-4 sm:px-6">
          <div className="flex items-center gap-3">
            <img
              src={LOGO}
              alt="FairPay logo"
              width={44}
              height={44}
              className="h-11 w-11 rounded-xl shadow-lg ring-1 ring-white/10"
            />
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-extrabold tracking-tight text-white">FairPay</h1>
                <span className="rounded-md bg-violet-500/20 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-violet-200 ring-1 ring-violet-400/30">
                  Milestone v1
                </span>
              </div>
              <p className="text-[11px] text-slate-400">Funded payroll vault on GenLayer StudioNet</p>
            </div>
          </div>
          <WalletBar
            role={role}
            setRole={setRole}
            wallet={wallet}
            setWallet={setWallet}
            muted={muted}
            setMuted={setMuted}
          />
        </div>
      </header>

      <main className="relative z-10 mx-auto max-w-7xl px-4 pb-16 pt-10 sm:px-6">
        <section className="grid gap-8 lg:grid-cols-[1.35fr_1fr] lg:items-center">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full bg-emerald-500/10 px-3 py-1 text-[11px] font-bold text-emerald-200 ring-1 ring-emerald-400/30">
              <ShieldCheck size={13} />
              PAPITO max-liability lock - 100% funded before work starts
            </div>
            <h2 className="mt-4 max-w-3xl text-4xl font-black leading-[1.05] tracking-tight text-white sm:text-5xl">
              Payroll that{" "}
              <span className="bg-gradient-to-r from-violet-300 via-fuchsia-300 to-cyan-300 bg-clip-text text-transparent">
                cannot be raided.
              </span>
            </h2>
            <p className="mt-4 max-w-2xl text-sm leading-relaxed text-slate-400">
              Every agreement locks the full maximum liability in an on-chain FPT vault. Settlement
              happens by two-party mutual co-sign or by a discrete 0/50/80/100 consensus band, and the
              employer can never withdraw unearned surplus while a submission, audit, or appeal is live.
            </p>
            <div className="mt-5 flex flex-wrap gap-2">
              <button
                onClick={() => scrollTo("guard-lab")}
                className="flex items-center gap-2 rounded-xl bg-violet-500/25 px-4 py-2.5 text-xs font-bold text-violet-100 ring-1 ring-violet-400/40 transition hover:bg-violet-500/35"
              >
                <Sparkles size={14} /> Open the guard lab
              </button>
              <a
                href={EVIDENCE}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-2 rounded-xl bg-white/5 px-4 py-2.5 text-xs font-bold text-slate-200 ring-1 ring-white/10 transition hover:bg-white/10"
              >
                <BookOpen size={14} /> Read the on-chain evidence
              </a>
              <a
                href={DEMO}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-2 rounded-xl bg-white/5 px-4 py-2.5 text-xs font-bold text-slate-200 ring-1 ring-white/10 transition hover:bg-white/10"
              >
                <Play size={14} /> Watch the 48s demo
              </a>
            </div>
            <div className="mt-5 flex flex-wrap gap-2">
              <Chip icon={<Vault size={12} className="text-violet-300" />}>Funded FPT custody</Chip>
              <Chip icon={<Handshake size={12} className="text-cyan-300" />}>Two-party co-sign</Chip>
              <Chip icon={<Coins size={12} className="text-emerald-300" />}>Discrete band audit</Chip>
              <Chip icon={<ShieldCheck size={12} className="text-amber-300" />}>No owner override</Chip>
            </div>
          </div>

          <div className="rounded-3xl bg-white/[0.03] p-5 ring-1 ring-white/10">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                Live deployment
              </span>
              <span
                className={
                  "flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[10px] font-bold ring-1 " +
                  (CONTRACT_READY
                    ? "bg-emerald-500/10 text-emerald-200 ring-emerald-400/30"
                    : "bg-amber-500/10 text-amber-200 ring-amber-400/30")
                }
              >
                <span className={"h-1.5 w-1.5 rounded-full " + (CONTRACT_READY ? "bg-emerald-400" : "bg-amber-400")} />
                {CONTRACT_READY ? "STUDIONET" : "PENDING"}
              </span>
            </div>
            <div className="mt-4 space-y-3 text-xs">
              <div className="flex items-center justify-between gap-3">
                <span className="text-slate-500">Contract</span>
                <a
                  href={EXPLORER}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center gap-1 font-mono text-violet-200 hover:text-violet-100"
                >
                  {shortAddress(CONTRACT_ADDRESS)} <ArrowUpRight size={11} />
                </a>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className="text-slate-500">Network</span>
                <span className="font-mono text-slate-300">StudioNet 61999</span>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className="text-slate-500">Runner</span>
                <span className="font-mono text-slate-300">py-genlayer:1jb45aa...</span>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className="text-slate-500">Tests</span>
                <span className="font-mono text-emerald-200">178 Direct Mode</span>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className="text-slate-500">Source identity</span>
                <span className="font-mono text-slate-300">4-way sha256</span>
              </div>
            </div>
            <div className="mt-4 flex items-center gap-2 rounded-xl bg-white/[0.03] p-2.5 text-[11px] text-slate-400 ring-1 ring-white/10">
              <Landmark size={13} className="text-cyan-300" />
              Vault balance, locks, and bonds are read live from the deployed contract below.
            </div>
          </div>
        </section>

        <section id="simulator" className="mt-14 scroll-mt-24">
          <SectionHeader
            index="01"
            icon={<Coins size={18} className="text-violet-300" />}
            title="What-if payroll, overtime and appeal liability"
            subtitle="Move base pay, the bonus cap, the appeal bond, and the consensus anchor. The lock, band, and split update with the same integer rules the contract uses."
          />
          <PayrollSimulator role={role} />
        </section>

        <section id="timeline" className="mt-14 scroll-mt-24">
          <SectionHeader
            index="02"
            icon={<Handshake size={18} className="text-cyan-300" />}
            title="Two-party mutual co-sign and appeal timeline"
            subtitle="OPEN to SUBMITTED to AUDITED with the appeal window locked, then APPEALED or CO-SIGNED, then SETTLED. A single signature never moves funds."
          />
          <TimelineStudio role={role} />
        </section>

        <section id="consensus" className="mt-14 scroll-mt-24">
          <SectionHeader
            index="03"
            icon={<FileCheck2 size={18} className="text-emerald-300" />}
            title="Consensus inspector and security guard lab"
            subtitle="See exactly what the model is asked, how the score is quantized, and what happens when an employer or a single party tries to break the guard."
          />
          <div id="guard-lab" className="grid scroll-mt-24 gap-4 xl:grid-cols-2">
            <ConsensusInspector />
            <GuardLab />
          </div>
        </section>

        <section id="live" className="mt-14 scroll-mt-24">
          <SectionHeader
            index="04"
            icon={<Vault size={18} className="text-violet-300" />}
            title="Live vault state"
            subtitle="Four to five gen_call reads on load, no polling. The invariant is checked directly against the deployed contract."
          />
          <LiveContract />
        </section>
      </main>

      <footer className="relative z-10 border-t border-white/5 bg-[#070b14]/80">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <img src={LOGO} alt="FairPay logo" width={24} height={24} className="h-6 w-6 rounded-md ring-1 ring-white/10" />
              <span className="text-xs font-bold text-slate-300">FairPay Milestone v1</span>
              <span className="text-[11px] text-slate-500">vault custody, co-sign, and consensus bands</span>
            </div>
            <div className="flex items-center gap-3 text-[11px]">
              <a href={REPO} target="_blank" rel="noreferrer" className="flex items-center gap-1 text-slate-400 hover:text-slate-200">
                <Code2 size={12} /> Repository
              </a>
              <a href={EVIDENCE} target="_blank" rel="noreferrer" className="flex items-center gap-1 text-slate-400 hover:text-slate-200">
                <BookOpen size={12} /> Evidence
              </a>
              <a href={EXPLORER} target="_blank" rel="noreferrer" className="flex items-center gap-1 text-slate-400 hover:text-slate-200">
                <ArrowUpRight size={12} /> Explorer
              </a>
            </div>
          </div>
          <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-[10px] text-slate-600">
            <span>
              {CONTRACT_READY ? "Contract " : "Awaiting deployment "}
              <span className="font-mono">{CONTRACT_ADDRESS}</span> on StudioNet (chain id 61999)
            </span>
            <span>Runner pinned py-genlayer:1jb45aa... - source byte-matched on chain - no owner or admin override</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
