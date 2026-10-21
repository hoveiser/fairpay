import { createClient } from "genlayer-js";
import { studionet } from "genlayer-js/chains";

// The address is replaced with the Milestone v1 deployment after
// scripts/deploy_studionet.py completes. CONTRACT_READY gates live reads so the
// page stays honest before that address exists.
export const CONTRACT_ADDRESS = "0x7E0895f9100DCf02306ed9d56D63B28105f172a9";
export const CONTRACT_READY = true;

const client = createClient({ chain: studionet });

export interface VaultState {
  vault_custody_balance: string;
  locked_payroll_escrows: string;
  active_appeal_bonds: string;
  invariant_holds: boolean;
  total_fpt_supply: string;
  native_backing: string;
  native_backed: boolean;
  agreement_count: number;
}

export interface Agreement {
  id: number;
  employer: string;
  worker: string;
  role: string;
  base_pay: string;
  bonus_cap: string;
  max_liability: string;
  locked_amount: string;
  status: string;
  appeal_window_sec: number;
  tranche_count: number;
  tranche_indexes: string[];
  receipt_id?: number;
}

export interface Tranche {
  agreement_id: number;
  index: number;
  status: string;
  payroll_band: string | null;
  delivery_anchor: number | null;
  evidence_authenticated: boolean | null;
  worker_payout: string;
  appeal_deadline_clock: number | null;
  appeal_resolved: boolean;
  bond_outcome: string;
}

export interface LiveState {
  vault: VaultState;
  invariant: boolean;
  count: number;
  agreement: Agreement | null;
  tranche: Tranche | null;
}

type Scalar = string | number | boolean;

async function read<T extends Scalar>(functionName: string, args: unknown[] = []): Promise<T> {
  // No local ABI override is passed to readContract. genlayer-js encodes the
  // call from the function name and args, and the deployed schema remains the
  // single source of truth.
  const result = await client.readContract({
    address: CONTRACT_ADDRESS as `0x${string}`,
    functionName,
    args: args as never[],
  });
  return result as unknown as T;
}

export async function loadLiveState(): Promise<LiveState> {
  // Three parallel reads plus up to two chained reads keep the initial load at
  // five gen_call requests, within the StudioNet rate-limit budget.
  const [vaultRaw, invariant, countRaw] = await Promise.all([
    read<string>("get_vault_state"),
    read<boolean>("check_vault_invariants"),
    read<number>("get_agreement_count"),
  ]);
  const count = Number(countRaw);
  let agreement: Agreement | null = null;
  let tranche: Tranche | null = null;
  if (count > 0) {
    // Use the first agreement so the panel shows the audited tranche even when
    // later agreements were settled by mutual co-sign and never had evidence.
    const snapshotId = 1;
    const raw = await read<string>("get_agreement", [snapshotId]);
    const parsed = JSON.parse(raw) as Agreement;
    if (parsed && parsed.id) agreement = parsed;
    if (agreement && agreement.tranche_indexes.length > 0) {
      const tRaw = await read<string>("get_tranche", [
        snapshotId,
        Number(agreement.tranche_indexes[0]),
      ]);
      const parsedTranche = JSON.parse(tRaw) as Tranche;
      if (parsedTranche && parsedTranche.status) tranche = parsedTranche;
    }
  }
  return {
    vault: JSON.parse(vaultRaw) as VaultState,
    invariant: Boolean(invariant),
    count,
    agreement,
    tranche,
  };
}
