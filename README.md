# 💰 FairPay

**AI-audited payroll with quality-tiered payouts on GenLayer — v0.2.0**

A decentralized payroll system where workers submit evidence of their work, AI validators audit the quality against an agreed rubric, and payments are automatically calculated based on the tier (HIGH/MEDIUM/LOW/UNVERIFIABLE).

## 📋 Contract Details

- **Network:** GenLayer Testnet Bradbury (LIVE)
- **Current Version:** v0.2.0
- **Contract Address:** `0x2A4B9AD63bC0Efc61F4dE06Edb053226fec16053`
- **Explorer:** [View on GenLayer Explorer](https://explorer-studio.genlayer.com/address/0x2A4B9AD63bC0Efc61F4dE06Edb053226fec16053)

## 🎯 What is FairPay?

FairPay solves the problem of **subjective work quality evaluation** in remote/knowledge work. Instead of human managers reviewing every task (expensive, biased, slow), AI validators fetch evidence URLs, evaluate against an agreed rubric, and determine the quality tier — then the contract automatically calculates and pays accordingly.

### Key Features

- **Quality-tiered payouts:** HIGH (1.25×), MEDIUM (1.0×), LOW (0.75×), UNVERIFIABLE (0×)
- **Anti-free-riding:** Budget must cover claimed hours at max multiplier before period starts
- **One-shot appeal:** Losing party can contest once; second AI round is final
- **Retry + dismiss:** 3 fetch attempts; if evidence unreachable, employer can dismiss the period
- **Payable custody:** Real GEN held by contract; paid out via on-chain transfers

## 🗺 State Machine

~~~
Job: create_job(worker, role, rubric, rate, appeal_window) [payable = budget]
  ↓
Period: submit_period(job_id, hours, items_json)
  → Budget check: hours × rate × 1.25 ≤ budget
  ↓
resolve_period → AI verdict: HIGH/MEDIUM/LOW/UNVERIFIABLE
  ↓
adjudicated → finalize → paid
  ↓
appeal (once) → disputed → resolve again → adjudicated (final)
  ↓
unresolvable (3 fetch failures) → dismiss / recover_budget
~~~

## 🧪 Test Matrix (all on Bradbury, verifiable on-chain)

### Round 1: Budget Guard + Happy Path

**Contract:** `0x2A4B9AD63bC0Efc61F4dE06Edb053226fec16053`

#### 1A: Budget Guard (Anti-Free-Riding)

- **Attempt:** `submit_period(job_id=1, hours=12, items=[...])`
- **Budget:** 10 GEN
- **Required:** 12 × 1 × 1.25 = 15 GEN
- **Result:** ❌ ERROR "Budget must cover claimed hours at max multiplier"
- **TX:** [submit_period (failed)](https://explorer-studio.genlayer.com/tx/0xee21f976a7a639b209bbb1b823f432f607e41f64cc31540bdd9f333dbfc50766)

#### 1B: Happy Path (MEDIUM)

- **submit_period:** job_id=1, hours=5, items=`[{"desc": "Built GenEscrow demo site with test results", "url": "https://hoveiser.github.io/genesrow-frontend/", "impact": "Live demo"}]`
- **resolve_period:** AI voted MEDIUM
- **finalize:** paid
- **Result:** pay = 5 × 1 × 1.0 = **5 GEN**
- **TX:** [submit_period](https://explorer-studio.genlayer.com/tx/0x576f90f33c2c9b1ec953b581db87baa3095d6293ffc12fe3d919c02aebfb6b7c) | [resolve_period](https://explorer-studio.genlayer.com/tx/0xc4c6727826271b6b154d0a318a40e15f97efd4415db11c0e12f6e46b4a826fe4) | [finalize](https://explorer-studio.genlayer.com/tx/0x78d903d0ee947a883ae9553c672d50a484d3be3e1650f737930aee1618e7217d)
- **Final state:** budget=5 GEN, status=paid, tier=MEDIUM

### Round 2: Fraudulent Claim + Appeal (LOW)

- **top_up:** +5 GEN (budget now 10)
- **submit_period:** job_id=1, hours=5, items=`[{"desc": "Built a native iOS app", "url": "https://hoveiser.github.io/hoveiser-genlayer-spinner/", "impact": "Mobile app shipped"}]`
- **resolve_period (1st):** AI voted LOW (claim doesn't match evidence)
- **appeal:** disputed
- **resolve_period (2nd, final):** AI voted LOW again
- **finalize:** paid
- **Result:** pay = 5 × 1 × 0.75 = **3.75 GEN**
- **TX:** [top_up](https://explorer-studio.genlayer.com/tx/0x555d83e66f8f237cdc42c7835e9b00cc9123cb09239ae308ec9f0d059b04c045) | [submit_period](https://explorer-studio.genlayer.com/tx/0x7af27639bfbfa4b0a26f112f275da493aad3447e7d2e155ffc393db09ed512ed) | [appeal](https://explorer-studio.genlayer.com/tx/0xaebaa9af331349361d2357947bf8683d8c445d4c95e71970b981fb75cfe8accc) | [finalize](https://explorer-studio.genlayer.com/tx/0x504bf6c17940cd44c9cf18f34f545a3c3c6777b4e9fe4a30bd0639dbe211d250)
- **Final state:** budget=6.25 GEN, status=paid, tier=LOW, appeals_used=1

### Round 3: Unreachable Evidence + Dismiss

- **submit_period:** job_id=1, hours=2, items=`[{"desc": "test", "url": "https://no-such-domain-xyz123.example.com/x"}]`
- **resolve_period (1st):** fetch_failures=1
- **resolve_period (2nd):** fetch_failures=2
- **resolve_period (3rd):** fetch_failures=3 → unresolvable
- **dismiss:** period dismissed, budget unchanged
- **Result:** pay=0, status=dismissed
- **TX:** [submit_period](https://explorer-studio.genlayer.com/tx/0x3f23b6bfc3811d8661d2cbb633bf439511315890b6e01262c2f38280fcc08960) | [resolve (3rd)](https://explorer-studio.genlayer.com/tx/0x81ecc5cb973c62c095a17c3e8eeb14fae8d58ed553133deb922dfdd3756ac3ff) | [dismiss](https://explorer-studio.genlayer.com/tx/0xe44fc299b5a565b62be694477952c347d56a6514b42ed1c4a53c35356484675a)
- **Final state:** budget=6.25 GEN (unchanged), status=dismissed

## 💡 Technical Implementation

### Payable Custody + Payout

- `@gl.public.write.payable` on `create_job` and `top_up` → contract receives and holds real GEN as payroll budget
- `gl.wasi.get_self_balance()` → tracks contract solvency
- Internal `gl_call_generic({'EthSend': {...}})` → performs on-chain transfer to worker
- Budget tracked per job; depleted by payouts

### Anti-Free-Riding Guard

Before any period starts, the contract verifies: `budget ≥ hours × rate × 1.25` (highest quality tier). This prevents workers from submitting periods the budget cannot pay for. The check happens at `submit_period`, before any work is evaluated.

### Time-Based Safety

- `gl.message_raw["datetime"]` → consensus-safe timestamp
- `appeal_window_sec` → time-bound appeal window
- Single open period per job → prevents budget double-spend

### AI-Powered Quality Audit

- Workers submit up to 3 evidence items (each with description, URL, claimed impact)
- Validators fetch all URLs via `gl.nondet.web.get`
- Visible text extracted (HTML/CSS stripped)
- Prompt includes role, rubric, claimed hours, and evidence
- Tier verdict (HIGH/MEDIUM/LOW/UNVERIFIABLE) via `gl.eq_principle.strict_eq`
- Payment multiplier applied: HIGH=1.25, MEDIUM=1.0, LOW=0.75, UNVERIFIABLE=0

### Retry + Dismiss

- Up to 3 fetch attempts before `unresolvable`
- No automatic payout on transient failures
- Employer can `dismiss` the period (budget unchanged) or worker can resubmit

### Authorization & State Machine

- `gl.message.sender_address == Address(...)` checks on every write method
- Strict state transitions: submitted → adjudicated → paid (or dismissed)
- Appeal limited to parties, once per period

## 🧪 How to Try It Yourself

1. Open https://studio.genlayer.com and deploy `contract.py`.
2. `create_job(worker, role, rubric, rate, appeal_window_sec)` with GEN value (budget).
3. `submit_period(job_id, hours, items_json)` where items is a JSON array of `{desc, url, impact}`.
4. `resolve_period(period_id)` → AI audits and returns tier.
5. `finalize(period_id)` after appeal window → worker paid.
6. Try fraudulent claims, unreachable URLs, appeals.

## 📂 Files

- `contract.py` — FairPay smart contract source code (v0.2.0)
- `README.md` — this documentation

## 🌐 Related

- **GenEscrow** (escrow with sealed evidence): https://github.com/hoveiser/genesrow
- **GenLayer Studio:** https://studio.genlayer.com
- **GenLayer Docs:** https://docs.genlayer.com

## License

MIT
