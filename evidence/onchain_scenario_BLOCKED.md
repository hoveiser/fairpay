# PART C.2 - on-chain run of the steward scenario: STATUS = BLOCKED

The steward scenario (LOW -> recover attempt -> appeal -> HIGH -> finalize
succeeds) is fully covered in Direct Mode against the real pinned GenVM runner
(see `direct_mode_and_lint.txt`, test `test_steward_recover_during_appeal_window_then_high_appeal`
for LOW/MEDIUM/UNVERIFIABLE). The live on-chain re-run of the same path against
the **redeployed v0.4.0** contract could NOT be executed from this environment.

## Why it is blocked (empirically verified, not assumed)

- `GENLAYER_PRIVATE_KEY` is not present in the environment or in any `.env`.
- The active `genlayer` CLI account `escrow-builder`
  (`0x3de43aa2f7162c80af98abe78222ae0cdf83c506`) has keystore `status: locked`;
  `genlayer deploy` fails at `Enter password to decrypt keystore` (headless, no
  keychain). Signing therefore requires either the keystore password or a raw
  private key, neither of which is available.
- No fixed v0.4.0 address exists yet to run the scenario against.

No transaction hashes are fabricated. Once the v0.4.0 contract is deployed, the
following will be recorded here (and in the README) and verified through the
explorer JSON API `https://explorer-studio.genlayer.com/api/transactions/<hash>`
with a real User-Agent - checking `status` AND the receipt execution result, and
comparing recipient balances before/after any payout:

1. create_job (payable) -> job id
2. submit_period (4h, sealed CID)
3. resolve_period -> LOW  (verify + read tier/pay)
4. recover_budget -> must withdraw only the excess above the 5 GEN max liability
   (verify budget >= 5 after; this is the steward's crux)
5. appeal -> disputed
6. resolve_period -> HIGH (pay 5)
7. finalize -> SUCCESS, worker balance +5 GEN (verify receipt execution + balance delta)
