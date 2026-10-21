import { useState } from "react";
import { Flame, ShieldCheck, Volume2, VolumeX, Wallet } from "lucide-react";
import { sound } from "../lib/sound";
import {
  connectMetaMask,
  getOrCreateBurner,
  shortAddress,
  type Role,
  type WalletIdentity,
} from "../lib/wallet";

interface Props {
  role: Role;
  setRole: (role: Role) => void;
  wallet: WalletIdentity | null;
  setWallet: (wallet: WalletIdentity | null) => void;
  muted: boolean;
  setMuted: (muted: boolean) => void;
}

export default function WalletBar({ role, setRole, wallet, setWallet, muted, setMuted }: Props) {
  const [error, setError] = useState("");

  function burner() {
    sound.click();
    setError("");
    setWallet(getOrCreateBurner());
  }

  async function metamask() {
    sound.click();
    setError("");
    try {
      setWallet(await connectMetaMask());
    } catch (err) {
      setError(err instanceof Error ? err.message : "MetaMask connection failed.");
    }
  }

  function toggleMute() {
    sound.click();
    setMuted(sound.toggle());
  }

  return (
    <div className="flex flex-col items-end gap-2">
      <div className="flex flex-wrap items-center justify-end gap-2">
        <div className="flex rounded-xl bg-white/5 p-1 ring-1 ring-white/10">
          {(["EMPLOYER", "WORKER"] as const).map((item) => (
            <button
              key={item}
              onClick={() => {
                sound.click();
                setRole(item);
              }}
              className={
                "rounded-lg px-2.5 py-1 text-[11px] font-bold tracking-wide transition " +
                (role === item
                  ? "bg-violet-500/25 text-violet-100 ring-1 ring-violet-400/40"
                  : "text-slate-400 hover:text-slate-200")
              }
            >
              {item === "EMPLOYER" ? "Employer" : "Worker"}
            </button>
          ))}
        </div>

        <button
          onClick={burner}
          className="flex items-center gap-1.5 rounded-xl bg-white/5 px-2.5 py-1.5 text-xs font-semibold text-slate-200 ring-1 ring-white/10 transition hover:bg-white/10"
          title="Create a one-click burner identity in this browser session"
        >
          <Flame size={14} className="text-orange-300" />
          Burner
        </button>

        <button
          onClick={metamask}
          className="flex items-center gap-1.5 rounded-xl bg-white/5 px-2.5 py-1.5 text-xs font-semibold text-slate-200 ring-1 ring-white/10 transition hover:bg-white/10"
          title="Connect MetaMask"
        >
          <Wallet size={14} className="text-cyan-300" />
          MetaMask
        </button>

        <button
          onClick={toggleMute}
          className="rounded-xl bg-white/5 p-2 text-slate-300 ring-1 ring-white/10 transition hover:bg-white/10"
          title={muted ? "Unmute UI sounds" : "Mute UI sounds"}
          aria-label={muted ? "Unmute UI sounds" : "Mute UI sounds"}
        >
          {muted ? <VolumeX size={15} /> : <Volume2 size={15} />}
        </button>
      </div>

      <div className="flex items-center gap-2 text-[11px] text-slate-500">
        {wallet ? (
          <>
            <ShieldCheck size={12} className="text-emerald-300" />
            <span className="font-mono text-slate-400">{shortAddress(wallet.address)}</span>
            <span className="rounded bg-white/5 px-1.5 py-0.5 uppercase tracking-wide">
              {wallet.kind}
            </span>
            <span className="hidden sm:inline">as {role.toLowerCase()}</span>
          </>
        ) : (
          <span>Demo identities only. No funds move from this page.</span>
        )}
      </div>
      {error && <p className="max-w-xs text-right text-[11px] text-rose-300">{error}</p>}
    </div>
  );
}
