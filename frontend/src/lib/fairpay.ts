export type Anchor = 0 | 50 | 80 | 100;

export type Band =
  | "FULL_BONUS_PAYOUT"
  | "STANDARD_TARGET_PAYOUT"
  | "PARTIAL_PRORATED_PAYOUT"
  | "REJECTED_NON_DELIVERY";

export const ANCHORS: readonly Anchor[] = [0, 50, 80, 100] as const;

export const BAND_BY_ANCHOR: Record<Anchor, Band> = {
  0: "REJECTED_NON_DELIVERY",
  50: "PARTIAL_PRORATED_PAYOUT",
  80: "STANDARD_TARGET_PAYOUT",
  100: "FULL_BONUS_PAYOUT",
};

export const BAND_LABEL: Record<Band, string> = {
  REJECTED_NON_DELIVERY: "Rejected - no verified delivery",
  PARTIAL_PRORATED_PAYOUT: "Partial - prorated base plus half bonus",
  STANDARD_TARGET_PAYOUT: "Standard target - base plus 80% bonus",
  FULL_BONUS_PAYOUT: "Full bonus - complete delivery with impact",
};

export const BAND_COLOR: Record<Band, string> = {
  REJECTED_NON_DELIVERY: "text-rose-300 bg-rose-500/10 ring-rose-400/30",
  PARTIAL_PRORATED_PAYOUT: "text-amber-200 bg-amber-500/10 ring-amber-400/30",
  STANDARD_TARGET_PAYOUT: "text-cyan-200 bg-cyan-500/10 ring-cyan-400/30",
  FULL_BONUS_PAYOUT: "text-emerald-200 bg-emerald-500/10 ring-emerald-400/30",
};

export function bandForAnchor(anchor: Anchor): Band {
  return BAND_BY_ANCHOR[anchor];
}

/** Mirror of _payout_for_anchor: base pay plus a prorated bonus share. */
export function payoutFor(base: number, bonus: number, anchor: Anchor): number {
  if (anchor === 0) return 0;
  return base + (bonus * anchor) / 100;
}

/** Mirror of _quantize_anchor: the same discrete ladder as the contract. */
export function quantize(score: number): Anchor {
  if (score >= 90) return 100;
  if (score >= 65) return 80;
  if (score >= 25) return 50;
  return 0;
}

export interface SimResult {
  maxLiability: number;
  payout: number;
  refund: number;
  band: Band;
  locked: number;
  lockPct: number;
  windowOpen: boolean;
}

export function simulate(
  base: number,
  bonus: number,
  anchor: Anchor,
  windowOpen: boolean,
): SimResult {
  const maxLiability = base + bonus;
  const payout = payoutFor(base, bonus, anchor);
  const refund = Math.max(0, maxLiability - payout);
  const locked = windowOpen ? maxLiability : payout;
  return {
    maxLiability,
    payout,
    refund,
    band: bandForAnchor(anchor),
    locked,
    lockPct: maxLiability === 0 ? 0 : (locked / maxLiability) * 100,
    windowOpen,
  };
}

export function fmt(value: number, digits = 2): string {
  const rounded = Math.round(value * 10 ** digits) / 10 ** digits;
  return rounded.toLocaleString("en-US", { maximumFractionDigits: digits });
}

export type GuardOutcome = "REVERT" | "NO_SETTLEMENT" | "ALLOWED";

export interface GuardResult {
  id: string;
  label: string;
  outcome: GuardOutcome;
  message: string;
  detail: string;
}

export function guardPrematureSurplus(windowOpen: boolean, appealPending: boolean): GuardResult {
  if (appealPending) {
    return {
      id: "premature",
      label: "Employer premature surplus clawback",
      outcome: "REVERT",
      message: "Appeal pending: liability locked",
      detail:
        "The worker appeal is unresolved, so 100% of max liability plus the bond stay in vault custody.",
    };
  }
  if (windowOpen) {
    return {
      id: "premature",
      label: "Employer premature surplus clawback",
      outcome: "REVERT",
      message: "Appeal window open: liability locked",
      detail:
        "The appeal clock is still running. 100% of max liability is locked, so there is no unearned surplus to withdraw.",
    };
  }
  return {
    id: "premature",
    label: "Employer premature surplus clawback",
    outcome: "ALLOWED",
    message: "Surplus released after finality",
    detail:
      "Every tranche is final, so only the amount above the final worker payout can be withdrawn.",
  };
}

export function guardSingleParty(signedBy: number, mismatch = false): GuardResult {
  if (mismatch) {
    return {
      id: "cosign",
      label: "Single-party co-sign",
      outcome: "REVERT",
      message: "Co-sign bps mismatch",
      detail:
        "The second party signed a different worker_payout_bps. The transaction reverts and no funds move.",
    };
  }
  if (signedBy < 2) {
    return {
      id: "cosign",
      label: "Single-party co-sign",
      outcome: "NO_SETTLEMENT",
      message: "Proposal recorded, zero funds moved",
      detail:
        "One signature is stored. Settlement requires the employer and worker to sign the exact same bps.",
    };
  }
  return {
    id: "cosign",
    label: "Single-party co-sign",
    outcome: "ALLOWED",
    message: "Both signatures match, settlement executes",
    detail: "worker_payout + employer_refund always equal the full max liability.",
  };
}

export function guardPostSettlement(settled: boolean): GuardResult {
  if (settled) {
    return {
      id: "postsettle",
      label: "Post-settlement mutation",
      outcome: "REVERT",
      message: "Agreement already settled",
      detail:
        "The agreement is final. Settlement receipts are immutable and no second proposal can reopen it.",
    };
  }
  return {
    id: "postsettle",
    label: "Post-settlement mutation",
    outcome: "ALLOWED",
    message: "Agreement is still open",
    detail: "A co-sign proposal is still accepted before settlement.",
  };
}

export const BAND_LADDER = ANCHORS.map((anchor) => ({
  anchor,
  band: BAND_BY_ANCHOR[anchor],
  label: BAND_LABEL[BAND_BY_ANCHOR[anchor]],
}));
