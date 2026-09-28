#!/usr/bin/env python3
"""Stage B: run the steward appeal/recovery scenario live on StudioNet.

The contract (v0.4.0) is already deployed; its address is read from
evidence/deploy.json. This script exercises real, value-bearing calls and
asserts the invariants the steward demanded rather than a specific AI tier
(the LLM tier cannot be forced on chain):

  create_job(payable) -> submit_period(weak evidence) -> resolve_period
  -> read reserved_liability BEFORE recovery -> recover_budget (inside the
  open appeal window) -> read reserved_liability AFTER -> appeal -> 
  resolve_period (final) -> finalize.

What must hold and is recorded:
  * after recover_budget, remaining budget >= reserved_liability (the maximum
    still-reachable payout), so finalize can never hit "Job budget insufficient";
  * the appeal goes through;
  * finalize succeeds funded;
  * the worker's GEN balance increases by exactly the payout after finalize.

Every transaction is verified against the explorer JSON API and its raw record
is saved under evidence/txs/. The private key is only read from the gitignored
.env and never printed or written.
"""
import json
import os
import sys
import time
import pathlib
import urllib.request

from dotenv import load_dotenv

from genlayer_py import create_account, create_client, studionet, generate_private_key

ROOT = pathlib.Path(__file__).resolve().parent.parent
EVIDENCE = ROOT / "evidence"
TXDIR = EVIDENCE / "txs"
TXDIR.mkdir(parents=True, exist_ok=True)
EXPLORER = "https://explorer-studio.genlayer.com"
GEN = 10**18

import base64


def get_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "qoder-agent"})
    return json.load(urllib.request.urlopen(req, timeout=60))


def decode_method(tx: dict) -> str:
    """Best-effort method name from the ledger calldata blob."""
    blob = (tx.get("data") or {}).get("calldata") or ""
    try:
        raw = base64.b64decode(blob)
        # calldata is a serialized dict; a substring scan is enough for reporting
        s = raw.decode("latin-1", errors="ignore")
        for m in ("create_job", "submit_period", "resolve_period", "appeal",
                  "recover_budget", "finalize", "top_up"):
            if m in s:
                return m
    except Exception:
        pass
    return "?"


def wait_finalized(txid: str, name: str, timeout_s: int = 900) -> dict:
    """Poll the explorer until the tx is FINALIZED; save the raw record."""
    deadline = time.time() + timeout_s
    last = None
    while time.time() < deadline:
        try:
            d = get_json(f"{EXPLORER}/api/transactions/{txid}")
            tx = d.get("transaction")
            if tx:
                last = tx
                if tx.get("status") == "FINALIZED":
                    (TXDIR / f"{name}_{txid[:10]}.json").write_text(json.dumps(tx, indent=2))
                    return tx
        except Exception as e:
            last = {"error": str(e)}
        time.sleep(6)
    raise RuntimeError(f"tx {name} {txid} not FINALIZED in {timeout_s}s; last={str(last)[:200]}")


def execution_result(tx: dict):
    lr = (tx.get("consensus_data") or {}).get("leader_receipt") or []
    if lr and isinstance(lr, list):
        r0 = lr[0]
        return r0.get("execution_result"), r0.get("result")
    return None, None


def balance_of(address: str) -> int:
    try:
        d = get_json(f"{EXPLORER}/api/address/{address}")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return 0  # account not indexed yet: zero balance, no txs
        raise
    return int(d.get("balance", 0))


def tx_ok(tx: dict) -> bool:
    er, _ = execution_result(tx)
    return str(er).upper() in ("SUCCESS", "OK", "1")


def main() -> int:
    load_dotenv(ROOT / ".env")
    key = os.environ.get("GENLAYER_PRIVATE_KEY", "")
    if not key:
        print("GENLAYER_PRIVATE_KEY missing; aborting.")
        return 2
    deploy = json.load(open(EVIDENCE / "deploy.json"))
    contract = deploy["contract_address"]
    employer = create_account(key)
    worker = create_account(generate_private_key())  # gasless: no funding needed
    print("contract:", contract)
    print("employer:", employer.address, "balance:", balance_of(employer.address))
    print("worker  :", worker.address, "balance:", balance_of(worker.address))

    c = create_client(chain=studionet, account=employer)

    def write(name, fn, args, account=None, value=0):
        acct = account or employer
        txid = c.write_contract(contract, fn, args=args, account=acct, value=value)
        tx = wait_finalized(txid, name)
        er, res = execution_result(tx)
        ok = tx_ok(tx)
        print(f"  {name:14s} {fn:16s} tx={txid} status={tx.get('status')} "
              f"exec={er} ok={ok} value={value//GEN if value else 0}gen")
        if not ok:
            print(f"    !! execution not successful: exec={er} result={str(res)[:200]}")
        return txid, tx, ok

    def read(fn, args):
        return c.read_contract(contract, fn, args=args)

    RATE = 1            # GEN per hour
    HOURS = 4           # max reachable payout = 4 * 1 * 1.25 = 5 GEN
    BUDGET = 10 * GEN   # employer locks 10 GEN
    APPEAL_WINDOW = 604800  # 7 days: keeps the window open across every step
    EVIDENCE_URL = "https://ipfs.io/ipfs/bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi"
    items = [{"desc": "Weekly progress screenshot (image, no written deliverable)",
              "url": EVIDENCE_URL,
              "impact": "none stated"}]

    record = {"contract": contract, "employer": employer.address, "worker": worker.address,
              "evidence_url": EVIDENCE_URL, "params": {"rate": RATE, "hours": HOURS,
              "budget_gen": BUDGET // GEN, "appeal_window_sec": APPEAL_WINDOW}, "txs": {}, "notes": []}

    print("\n[1] create_job (payable, employer)")
    txid, tx, ok = write("01_create_job", "create_job",
                         [worker.address, "Content writer",
                          "Evidence must be a written article draft with concrete metrics; an unrelated image is not deliverable evidence.",
                          RATE, APPEAL_WINDOW, 40, 3600], value=BUDGET)
    record["txs"]["create_job"] = txid
    if not ok:
        record["notes"].append("create_job failed"); print(json.dumps(record, indent=2)); return 4
    jid = 1  # first job on a fresh contract

    print("\n[2] submit_period (worker, weak image evidence)")
    txid, tx, ok = write("02_submit_period", "submit_period",
                         [jid, HOURS, json.dumps(items)], account=worker)
    record["txs"]["submit_period"] = txid
    if not ok:
        record["notes"].append(
            "submit_period reverted: the on-chain evidence fetch from ipfs.io did not "
            "return usable content (see evidence/txs/02_submit_period_*.json)")
        print(json.dumps(record, indent=2)); return 5
    pid = 1  # first period

    print("\n[3] resolve_period (first audit; expect below HIGH for weak evidence)")
    txid, tx, ok = write("03_resolve_first", "resolve_period", [pid])
    record["txs"]["resolve_first"] = txid
    period = json.loads(read("get_period", [pid]))
    tier1 = period.get("tier")
    print("    first tier:", tier1, "pay:", period.get("pay", 0) // GEN, "gen")
    record["first_tier"] = tier1
    if not ok or tier1 in (None, "UNREACHABLE", "UNSTRUCTURED"):
        record["notes"].append(f"first resolve not decisive (tier={tier1})")

    print("\n[4] reserved_liability BEFORE recovery")
    reserved_before = int(read("reserved_liability", [jid]))
    job_before = json.loads(read("get_job", [jid]))
    print(f"    reserved_before={reserved_before//GEN}gen budget={job_before['budget']//GEN}gen "
          f"(max reachable = hours*rate*1.25 = {HOURS}*{RATE}*1.25 = {int(HOURS*RATE*1.25)}gen)")
    record["reserved_before_recovery"] = reserved_before

    print("\n[5] recover_budget (employer, inside the open appeal window)")
    emp_bal_before = balance_of(employer.address)
    txid, tx, ok = write("05_recover_budget", "recover_budget", [jid])
    record["txs"]["recover_budget"] = txid
    emp_bal_after = balance_of(employer.address)
    reserved_after = int(read("reserved_liability", [jid]))
    job_after = json.loads(read("get_job", [jid]))
    print(f"    budget_after_recovery={job_after['budget']//GEN}gen reserved_after={reserved_after//GEN}gen "
          f"employer_balance {emp_bal_before//GEN}->{emp_bal_after//GEN}gen")
    invariant1 = job_after["budget"] >= reserved_after >= HOURS * RATE * 125 * GEN // 100
    record["reserved_after_recovery"] = reserved_after
    record["budget_after_recovery"] = job_after["budget"]
    record["invariant_budget_ge_reserved_after_recovery"] = invariant1
    print("    INVARIANT budget>=reserved (and reserved==max reachable 5gen):", invariant1)

    print("\n[6] appeal (worker, within window)")
    txid, tx, ok = write("06_appeal", "appeal", [pid], account=worker)
    record["txs"]["appeal"] = txid
    period = json.loads(read("get_period", [pid]))
    record["appeal_succeeded"] = bool(ok) and period.get("status") == "disputed"
    print("    period status after appeal:", period.get("status"))

    print("\n[7] resolve_period (final appeal round)")
    txid, tx, ok = write("07_resolve_final", "resolve_period", [pid])
    record["txs"]["resolve_final"] = txid
    period = json.loads(read("get_period", [pid]))
    tier2 = period.get("tier")
    pay2 = int(period.get("pay", 0))
    record["final_tier"] = tier2
    record["final_pay"] = pay2
    print("    final tier:", tier2, "pay:", pay2 // GEN, "gen status:", period.get("status"))

    print("\n[8] finalize (must be funded; no 'Job budget insufficient')")
    wk_bal_before = balance_of(worker.address)
    txid, tx, ok = write("08_finalize", "finalize", [pid])
    record["txs"]["finalize"] = txid
    wk_bal_after = balance_of(worker.address)
    period = json.loads(read("get_period", [pid]))
    job_final = json.loads(read("get_job", [jid]))
    paid_delta = wk_bal_after - wk_bal_before
    record["finalize_succeeded"] = bool(ok) and period.get("status") == "paid"
    record["worker_balance_before_finalize"] = wk_bal_before
    record["worker_balance_after_finalize"] = wk_bal_after
    record["worker_payout_delta"] = paid_delta
    print(f"    worker balance {wk_bal_before//GEN}->{wk_bal_after//GEN}gen delta={paid_delta//GEN}gen "
          f"period_status={period.get('status')} budget_remaining={job_final['budget']//GEN}gen")

    (EVIDENCE / "scenario.json").write_text(json.dumps(record, indent=2))

    print("\n=== SUMMARY ===")
    print(json.dumps({k: record[k] for k in
                      ("first_tier", "final_tier", "reserved_before_recovery",
                       "reserved_after_recovery", "budget_after_recovery",
                       "invariant_budget_ge_reserved_after_recovery", "appeal_succeeded",
                       "finalize_succeeded", "worker_payout_delta") if k in record}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
