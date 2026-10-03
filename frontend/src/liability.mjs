// Port of the contract's financial gate: _max_liability() and the tier
// multiplier table in contracts/contract.py. Values are atto-GEN (x10^18) on
// chain and use integer ceiling so a reserve can never under-count.

export const TIER_MULTIPLIER = { HIGH: 125, MEDIUM: 100, LOW: 75, UNVERIFIABLE: 0 };
export const TIERS = ["HIGH", "MEDIUM", "LOW", "UNVERIFIABLE"];
const ATTO = 1000000000000000000n;

function ceilDiv(a, b) {
  return (a + b - 1n) / b;
}

// hours * rate * 125 / 100, rounded UP, in atto-GEN. rate is GEN/hour (integer).
export function maxLiabilityAtto(hours, rate) {
  const h = BigInt(Math.max(0, Math.floor(hours)));
  const r = BigInt(Math.max(0, Math.floor(rate)));
  return ceilDiv(h * r * 125n * ATTO, 100n);
}

// Actual payout for a settled tier: hours * rate * mult / 100 (integer div,
// matching the contract's floor on the pay line), in atto-GEN.
export function payoutAtto(hours, rate, tier) {
  const h = BigInt(Math.max(0, Math.floor(hours)));
  const r = BigInt(Math.max(0, Math.floor(rate)));
  const mult = BigInt(TIER_MULTIPLIER[tier] ?? 0);
  return (h * r * mult * ATTO) / 100n;
}

export function attoToGen(atto) {
  return Number(BigInt(atto)) / 1e18;
}

export function formatGen(atto, digits = 3) {
  const g = attoToGen(atto);
  return g.toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: digits });
}
