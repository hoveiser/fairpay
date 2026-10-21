# FairPay Milestone v1 evidence

All values below are generated from measured files, on-chain reads, and
explorer receipts. Do not hand edit this file; rebuild it with
`python scripts/build_deployment_evidence.py <commit>`.

## Deployment

| Field | Value |
| --- | --- |
| Network | StudioNet, chain id 61999 |
| Contract | `0x56565F5Cf8eDF85ed5a82cA340Af9Ce0FBFF0E0a` |
| Explorer | https://explorer-studio.genlayer.com/address/0x56565F5Cf8eDF85ed5a82cA340Af9Ce0FBFF0E0a |
| Deploy tx | `0xc976eb0b8511a0deb4028a6f63b64ea10f60115ae727b6486525470edce5dbed` |
| Deployed commit | `0a2b303cdd5ebcb6a8ef35a6b3242b1aae41549e` |
| Contract bytes | 37578 |
| Contract tests | 179 passing Direct Mode tests |
| Lint | genvm-lint check passed |

## Four-way sha256 identity

| Source | sha256 |
| --- | --- |
| Local LF file | `796f4661a0bf8d1830ca898196260b71dc1c7103d46fc019c417e547985a8f17` |
| Git blob at deployed commit | `796f4661a0bf8d1830ca898196260b71dc1c7103d46fc019c417e547985a8f17` |
| Raw GitHub blob at deployed commit | `796f4661a0bf8d1830ca898196260b71dc1c7103d46fc019c417e547985a8f17` |
| StudioNet `gen_getContractCode` | `796f4661a0bf8d1830ca898196260b71dc1c7103d46fc019c417e547985a8f17` |

Four-way match: **TRUE**.

## Live Milestone v1 scenario

| Step | Result |
| --- | --- |
| Deposit and FPT mint | pass |
| Agreement 1 max liability lock | pass |
| Live audit FINALIZED and MAJORITY_AGREE | pass |
| Audit band | `FULL_BONUS_PAYOUT` at anchor 100 |
| Audit payout | 80 GEN |
| Single-party co-sign does not settle | pass |
| Matching co-sign settles at 7000 bps | pass |
| Appeal accepted and resolved by consensus | pass |
| Settlement receipt matches the payout | pass |
| transfer_tokens moved the exact amount | pass |
| Vault invariant holds | pass |
| Guard reverts matched | 3 of 3 |

### Expected guard reverts

| Guard | Expected message | Matched on chain | Tx |
| --- | --- | --- | --- |
| premature employer surplus withdrawal | `Appeal window open: liability locked` | yes | `0xf73dc4c6b69d72116356de1eb09d6bd6d79360e9e4c56ea5545f9b09c6f2125b` |
| post-settlement mutation | `Agreement already settled` | yes | `0x81b8adf729cc45e4f6abfb36b74b31c42929ccff124a62b1db5252082119972f` |
| single-party co-sign bps mismatch | `Co-sign bps mismatch` | yes | `0x231aede6691afcd46daa1112c86eaac4cf6af01052b764d23b939d67d6ad2dcb` |

### Settlement receipt

| Field | Value |
| --- | --- |
| Receipt id | 3 |
| Worker payout | 76 GEN |
| Employer refund | 4 GEN |
| Payroll band | `STANDARD_TARGET_PAYOUT` |
| Delivery anchor | 80 |
| Bonds refunded | 0 GEN |
| Bonds forfeited | 2 GEN |

### Vault custody

| Field | Value |
| --- | --- |
| Vault custody balance | 0 |
| Locked payroll escrows | 0 |
| Active appeal bonds | 0 |
| Invariant holds | True |

Raw records: `evidence/milestone_scenario.json`, `evidence/milestone_txs/`.

## Reproduce

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
genvm-lint check contracts/contract.py
pytest tests/ -q
python scripts/deploy_studionet.py
python scripts/run_milestone_scenario.py <deployed-commit>
python scripts/build_deployment_evidence.py <deployed-commit>
```
