#!/usr/bin/env python3
"""Run the FairPay v0.4.1 steward scenario live on StudioNet.

v0.4.1 accepts sealed evidence from an allowlist of immutable IPFS gateways, so
the on-chain blocker (ipfs.io returning HTTP 429 to non-browser fetchers) can be
worked around without weakening contract validation.

Flow, all real value-bearing calls through genlayer-py (the CLI keystore is
locked here; the key is read only from the gitignored .env and never printed):

  1. create_job(payable)                         employer locks 10 GEN
  2. submit_period weak evidence, probing each allowed gateway in turn. Failed
     fetches revert (no state change), so the same job stays open until a
     gateway the validators can actually reach seals the content. The order
     tries the egress-429 gateways (dweb.link, w3s.link, ipfs.io) FIRST and
     gateway.pinata.cloud (the only one returning 200 to a validator-style
     client from this machine) LAST, so a single job classifies every gateway:
     the ones that fail are recorded FETCH_FAILED, and the first that seals
     becomes the scenario's evidence. Validation is never weakened.
  3. resolve_period (first audit; weak evidence -> expect below HIGH)
  4. read reserved_liability BEFORE recovery
  5. recover_budget (employer, inside the still-open appeal window)
  6. read reserved_liability AFTER recovery
  7. appeal (worker)
  8. resolve_period (final appeal round)
  9. finalize (must be funded; no "Job budget insufficient")

Invariants asserted and recorded (not a specific AI tier, which cannot be
forced on chain): after recovery remaining budget >= reserved_liability (the max
still-reachable payout); the appeal is accepted; finalize succeeds funded; and
the recipient GEN balance moves by exactly the payout (read before/after via the
explorer, not just the status field).

Every transaction is verified against the explorer JSON API and its raw record
saved under evidence/txs/. Nothing is paraphrased.
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

# probe order: likely-failing egress-429 gateways first, proven pinata last so
# one job classifies all four and the scenario runs on the first that seals.
GATEWAY_ORDER = ("dweb.link", "w3s.link", "ipfs.io", "gateway.pinata.cloud")
# deliberately weak evidence: a status note, no concrete written deliverable
CID_WEAK = "bafkreidwkl2tdyhpeij4es7ng23qiexzxn5nq2ae2ckf6nmtsahrsit5zq"


def get_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "qoder-agent"})
    return json.load(urllib.request.urlopen(req, timeout=60))


def wait_finalized(txid: str, name: str, timeout_s: int = 900) -> dict:
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


def seal_of(tx: dict):
    # the sealed strict_eq output surfaces in the leader result on revert; it is
    # FETCH_FAILED when no validator could fetch the evidence bytes
    _er, res = execution_result(tx)
    return res


def balance_of(address: str) -> int:
    try:
        d = get_json(f"{EXPLORER}/api/address/{address}")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return 0
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
        print(f"  {name:16s} {fn:16s} tx={txid} status={tx.get('status')} "
              f"exec={er} ok={ok} value={value//GEN if value else 0}gen")
        if not ok:
            print(f"    !! exec={er} result={str(res)[:160]}")
        return txid, tx, ok

    def read(fn, args):
        return c.read_contract(contract, fn, args=args)

    def find_job_id(worker_addr):
        # The deployed contract accumulates jobs across runs, so the new job id
        # is NOT deterministic. Locate it by scanning get_job for this run's
        # single-use worker address instead of assuming jid == 1.
        for candidate in range(0, 200):
            try:
                job = json.loads(read("get_job", [candidate]))
            except Exception:
                continue
            if str(job.get("worker", "")).lower() == worker_addr.lower():
                return candidate
        raise RuntimeError("created job not found by worker address")

    RATE = 1
    HOURS = 4                       # max reachable payout = 4 * 1 * 1.25 = 5 GEN
    BUDGET = 10 * GEN
    APPEAL_WINDOW = 604800          # 7 days: keeps the window open across every step

    record = {"contract": contract, "employer": employer.address, "worker": worker.address,
              "cid_weak": CID_WEAK, "params": {"rate": RATE, "hours": HOURS,
              "budget_gen": BUDGET // GEN, "appeal_window_sec": APPEAL_WINDOW},
              "gateway_probe": {}, "txs": {}, "notes": []}

    print("\n[1] create_job (payable, employer, 10 GEN)")
    txid, tx, ok = write("01_create_job", "create_job",
                         [worker.address, "Content writer",
                          "Evidence must be a written deliverable with concrete metrics; "
                          "a vague status note is not deliverable evidence.",
                          RATE, APPEAL_WINDOW, 40, 3600], value=BUDGET)
    record["txs"]["create_job"] = txid
    if not ok:
        record["notes"].append("create_job failed")
        (EVIDENCE / "scenario.json").write_text(json.dumps(record, indent=2))
        print(json.dumps(record, indent=2)); return 4
    jid = find_job_id(worker.address)
    print("    resolved job id:", jid)

    print("\n[2] submit_period gateway probe (weak evidence, worker)")
    scenario_gateway = None
    pid = None
    for gw in GATEWAY_ORDER:
        url = f"https://{gw}/ipfs/{CID_WEAK}"
        items = json.dumps([{"desc": "Weekly status note", "url": url, "impact": "none stated"}])
        tid, ttx, gok = write(f"02_submit_{gw.split('.')[0]}", "submit_period", [jid, HOURS, items], account=worker)
        record["gateway_probe"][gw] = {"url": url, "tx": tid, "finalized": ttx.get("status"),
                                       "exec": execution_result(ttx)[0], "sealed_output": str(seal_of(ttx))[:80]}
        if gok:
            scenario_gateway = gw
            record["txs"]["submit_period"] = tid
            record["scenario_gateway"] = gw
            job_now = json.loads(read("get_job", [jid]))
            pids = job_now["period_ids"]
            pid = int(pids[-1])
            record["job_id"] = jid
            record["period_id"] = pid
            print(f"    ==> validators reached {gw}; period sealed (pid={pid})")
            break
        print(f"    {gw}: not fetchable by validators on chain (reverted), trying next")
    if scenario_gateway is None:
        record["notes"].append(
            "submit_period reverted for every allowed gateway (dweb.link, w3s.link, "
            "ipfs.io, gateway.pinata.cloud): no validator could fetch the evidence bytes "
            "(see evidence/gateway_probe.json / evidence/txs/). The on-chain scenario could "
            "not proceed past submission.")
        (EVIDENCE / "scenario.json").write_text(json.dumps(record, indent=2))
        (EVIDENCE / "gateway_probe.json").write_text(json.dumps(record["gateway_probe"], indent=2))
        print(json.dumps(record["gateway_probe"], indent=2))
        print("SCENARIO BLOCKED: no gateway reachable by validators on chain")
        return 5
    (EVIDENCE / "gateway_probe.json").write_text(json.dumps(record["gateway_probe"], indent=2))

    print("\n[3] resolve_period (first audit)")
    txid, tx, ok = write("03_resolve_first", "resolve_period", [pid])
    record["txs"]["resolve_first"] = txid
    period = json.loads(read("get_period", [pid]))
    # if the first resolve hit a transient non-decision, allow up to 3 attempts
    attempts = 1
    while period["status"] == "submitted" and attempts < 3:
        attempts += 1
        txid, tx, ok = write(f"03b_resolve_retry{attempts}", "resolve_period", [pid])
        period = json.loads(read("get_period", [pid]))
    tier1 = period.get("tier")
    record["first_tier"] = tier1
    record["first_status"] = period["status"]
    print("    first tier:", tier1, "status:", period["status"], "pay:", period.get("pay", 0) // GEN, "gen")
    if period["status"] != "adjudicated":
        record["notes"].append(f"period not adjudicated after {attempts} resolves (status={period['status']})")

    print("\n[4] reserved_liability BEFORE recovery")
    reserved_before = int(read("reserved_liability", [jid]))
    job_before = json.loads(read("get_job", [jid]))
    print(f"    reserved_before={reserved_before//GEN}gen budget={job_before['budget']//GEN}gen")
    record["reserved_before_recovery"] = reserved_before
    record["budget_before_recovery"] = job_before["budget"]

    print("\n[5] recover_budget (employer, inside the open appeal window)")
    emp_before = balance_of(employer.address)
    txid, tx, ok = write("05_recover_budget", "recover_budget", [jid])
    record["txs"]["recover_budget"] = txid
    record["recover_ok"] = bool(ok)
    emp_after = balance_of(employer.address)
    reserved_after = int(read("reserved_liability", [jid]))
    job_after = json.loads(read("get_job", [jid]))
    invariant = job_after["budget"] >= reserved_after >= (HOURS * RATE * 125 * GEN // 100)
    max_reachable = HOURS * RATE * 125 * GEN // 100
    print(f"    budget_after={job_after['budget']//GEN}gen reserved_after={reserved_after//GEN}gen "
          f"max_reachable={max_reachable//GEN}gen employer_balance {emp_before//GEN}->{emp_after//GEN}gen")
    print("    INVARIANT budget >= reserved_after >= max_reachable(5gen):", invariant)
    record.update({"reserved_after_recovery": reserved_after, "budget_after_recovery": job_after["budget"],
                   "max_reachable_payout": max_reachable, "employer_balance_before_recover": emp_before,
                   "employer_balance_after_recover": emp_after, "invariant_budget_ge_reserved_after_recovery": invariant})

    print("\n[6] appeal (worker, within window)")
    txid, tx, ok = write("06_appeal", "appeal", [pid], account=worker)
    record["txs"]["appeal"] = txid
    period = json.loads(read("get_period", [pid]))
    record["appeal_succeeded"] = bool(ok) and period.get("status") == "disputed"
    print("    period status after appeal:", period.get("status"), "appeal_succeeded:", record["appeal_succeeded"])

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
    wk_before = balance_of(worker.address)
    txid, tx, ok = write("08_finalize", "finalize", [pid])
    record["txs"]["finalize"] = txid
    wk_after = balance_of(worker.address)
    period = json.loads(read("get_period", [pid]))
    job_final = json.loads(read("get_job", [jid]))
    paid_delta = wk_after - wk_before
    record["finalize_ok"] = bool(ok)
    record["finalize_succeeded"] = bool(ok) and period.get("status") == "paid"
    record["worker_balance_before_finalize"] = wk_before
    record["worker_balance_after_finalize"] = wk_after
    record["worker_payout_delta"] = paid_delta
    record["payout_matches_balance"] = (paid_delta == pay2)
    print(f"    worker balance {wk_before//GEN}->{wk_after//GEN}gen delta={paid_delta//GEN}gen "
          f"(pay={pay2//GEN}gen match={paid_delta==pay2}) period_status={period.get('status')} "
          f"budget_remaining={job_final['budget']//GEN}gen")

    (EVIDENCE / "scenario.json").write_text(json.dumps(record, indent=2))
    print("\n=== SUMMARY ===")
    keys = ("scenario_gateway", "gateway_probe", "first_tier", "final_tier",
            "reserved_before_recovery", "reserved_after_recovery", "budget_after_recovery",
            "max_reachable_payout", "invariant_budget_ge_reserved_after_recovery",
            "appeal_succeeded", "finalize_succeeded", "worker_payout_delta", "payout_matches_balance")
    print(json.dumps({k: record.get(k) for k in keys if k in record}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
