# FairPay Milestone v1 evidence

All values below are generated from measured files, on-chain reads, and
explorer receipts. Do not hand edit this file; rebuild it with
`python scripts/build_deployment_evidence.py <commit>`.

## Deployment

| Field | Value |
| --- | --- |
| Network | StudioNet, chain id 61999 |
| Contract | `0x7E0895f9100DCf02306ed9d56D63B28105f172a9` |
| Explorer | https://explorer-studio.genlayer.com/address/0x7E0895f9100DCf02306ed9d56D63B28105f172a9 |
| Deploy tx | `0x9d3ac0a2a581dda1986fafb60717b6a29dc14f70066177edaf2189b860959770` |
| Deployed commit | `552ea90b49f55e446134954d4fc7731adfa615e2` |
| Contract bytes | 37560 |
| Contract tests | 180 passing Direct Mode tests |
| Lint | genvm-lint check passed |

## Four-way sha256 identity

| Source | sha256 |
| --- | --- |
| Local LF file | `c243cc5ffbc6243c0da2de45a696f49691280918afa7e222e90ed0c182a07425` |
| Git blob at deployed commit | `c243cc5ffbc6243c0da2de45a696f49691280918afa7e222e90ed0c182a07425` |
| Raw GitHub blob at deployed commit | `c243cc5ffbc6243c0da2de45a696f49691280918afa7e222e90ed0c182a07425` |
| StudioNet `gen_getContractCode` | `c243cc5ffbc6243c0da2de45a696f49691280918afa7e222e90ed0c182a07425` |

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
| premature employer surplus withdrawal | `Appeal window open: liability locked` | yes | `0x572e124baf95a61eeb5eb191085bb4d56b9a4d40c781355f2cc2568638d8cd37` |
| post-settlement mutation | `Agreement already settled` | yes | `0x5312732e3ff0e4eee8c25e73704962d8facc3a95320a6d0374a7c1dd6bdb7183` |
| single-party co-sign bps mismatch | `Co-sign bps mismatch` | yes | `0x3435547d0839594001e6a7f980736f8142463fb729df917ffe6f8aa9e5b27823` |

### Settlement receipt

| Field | Value |
| --- | --- |
| Receipt id | 3 |
| Worker payout | 80 GEN |
| Employer refund | 0 GEN |
| Payroll band | `FULL_BONUS_PAYOUT` |
| Delivery anchor | 100 |
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
