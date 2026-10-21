import { createAccount, generatePrivateKey } from "genlayer-js";

export type Role = "EMPLOYER" | "WORKER";
export type WalletKind = "burner" | "metamask";

const BURNER_KEY = "fairpay.burner.key";

export interface WalletIdentity {
  kind: WalletKind;
  address: string;
}

/**
 * One-click burner identity for the demo. The private key stays in
 * sessionStorage and is never rendered. It holds no funds on this page; the
 * live value-bearing flow is recorded in docs/evidence.md.
 */
export function getOrCreateBurner(): WalletIdentity {
  let key = sessionStorage.getItem(BURNER_KEY);
  if (!key) {
    key = generatePrivateKey();
    sessionStorage.setItem(BURNER_KEY, key);
  }
  const account = createAccount(key as `0x${string}`);
  return { kind: "burner", address: account.address };
}

export async function connectMetaMask(): Promise<WalletIdentity> {
  const provider = window.ethereum;
  if (!provider) {
    throw new Error("MetaMask is not installed in this browser.");
  }
  const accounts = (await provider.request({ method: "eth_requestAccounts" })) as string[];
  if (!accounts || accounts.length === 0) {
    throw new Error("MetaMask returned no account.");
  }
  return { kind: "metamask", address: accounts[0] };
}

export function shortAddress(address: string): string {
  if (!address || address.length < 12) return address || "";
  return address.slice(0, 6) + "..." + address.slice(-4);
}
