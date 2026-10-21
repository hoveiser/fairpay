#!/usr/bin/env python3
"""Run the FairPay Milestone v1 scenario live on StudioNet.

Every step is a real transaction, checked through the explorer JSON API. The
evidence key is read from the gitignored .env and never printed. Validator
records returned by the explorer can contain node_config.private_key fields, so
every saved receipt is passed through a recursive redactor before it touches
disk.

Flow:
  1. employer deposits native GEN and mints FPT 1:1
  2. employer transfers FPT to the worker for the appeal bond
  3. employer creates agreement 1 (80 GEN max liability locked)
  4. worker submits a tranche with commit-pinned raw GitHub evidence
  5. live consensus audit (prompt_comparative) and consensus vote accounting
  6. guard revert: employer surplus recovery during the open appeal window
  7. agreement 2: single-party co-sign does not settle; matching co-sign does
  8. guard revert: co-sign basis-point mismatch
  9. guard revert: post-settlement mutation
 10. agreement 1: worker appeal, live appeal resolution, settlement
 11. worker transfer_tokens after the payout claim
 12. vault invariant and final state reads

Output: evidence/milestone_scenario.json plus sanitized receipts in
evidence/milestone_txs/.
"""
import base64
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.request

from dotenv import load_dotenv

from genlayer_py import create_account, create_client, generate_private_key, studionet

ROOT = pathlib.Path(__file__).resolve().parent.parent
EVIDENCE = ROOT / "evidence"
TXDIR = EVIDENCE / "milestone_txs"
TXDIR.mkdir(parents=True, exist_ok=True)
EXPLORER = "https://explorer-studio.genlayer.com"
GEN = 10**18
BASE = 60 * GEN
BONUS = 20 * GEN
MAX_LIABILITY = BASE + BONUS
APPEAL_WINDOW = 604800  # 7 days: stays open for the whole scenario
BOND = 2 * GEN
DEPOSIT = 200 * GEN
WORKER_FUNDING = 5 * GEN
ROLE = "release engineer"
RUBRIC = (
    "Deliver a Milestone v1 release note that explains the funded FPT vault, the "
    "PAPITO maximum-liability lock, the two-party mutual co-sign, and the discrete "
    "consensus band audit, and lists the test checklist and the deployed contract address."
)
TIMESHEET = (
    "Completed the Milestone v1 release note and security checklist. The note documents "
    "the funded FPT vault, the PAPITO lock, the co-sign guard, the 0/50/80/100 anchor "
    "ladder, and the live deployment proof."
)


def get_json(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": "qoder-agent"})
    return json.load(urllib.request.urlopen(req, timeout=timeout))


def redact(value):
    """Remove private keys and secrets from any nested explorer response."""
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            lower = str(key).lower()
            if "private_key" in lower or "secret" in lower or lower in ("r", "s", "v"):
                out[key] = "<redacted>"
            else:
                out[key] = redact(item)
        return out
    if isinstance(value, list):
        return [redact(x) for x in value]
    return value


def wait_finalized(txid, name, timeout_s=1200):
    deadline = time.time() + timeout_s
    last = None
    while time.time() < deadline:
        try:
            payload = get_json(EXPLORER + "/api/transactions/" + txid)
            tx = payload.get("transaction")
            if tx:
                last = tx
                if tx.get("status") == "FINALIZED":
                    safe = redact(tx)
                    (TXDIR / (name + "_" + txid[:10] + ".json")).write_text(
                        json.dumps(safe, indent=2), encoding="utf-8"
                    )
                    return safe
        except Exception as exc:
            last = {"error": str(exc)}
        time.sleep(6)
    raise RuntimeError("tx " + name + " " + txid + " not FINALIZED: " + str(last)[:240])


def leader_receipt(tx):
    receipts = (tx.get("consensus_data") or {}).get("leader_receipt") or []
    return receipts[0] if receipts else {}


def execution_result(tx):
    receipt = leader_receipt(tx)
    return receipt.get("execution_result"), receipt.get("result")


def error_text(tx):
    receipt = leader_receipt(tx)
    stderr = (receipt.get("genvm_result") or {}).get("stderr") or ""
    lines = [line.strip() for line in stderr.splitlines() if line.strip()]
    if lines:
        return lines[-1][:300]
    # gl.vm.UserError is returned as result = b"\x01" + message, not on stderr.
    raw = receipt.get("result") or ""
    try:
        decoded = base64.b64decode(raw).decode("utf-8", "replace")
        text = "".join(ch for ch in decoded if ch.isprintable()).strip()
        if text and text != "exit_code 1":
            return text[:300]
    except Exception:
        pass
    return ""


def consensus_summary(tx):
    votes = list(((tx.get("consensus_data") or {}).get("votes") or {}).values())
    agree = votes.count("agree")
    total = len(votes)
    if total == 0:
        status = "UNKNOWN"
    elif agree * 2 > total:
        status = "MAJORITY_AGREE"
    else:
        status = "NO_MAJORITY"
    receipt = leader_receipt(tx)
    return {
        "status": status,
        "agree": agree,
        "total": total,
        "nondet_disagree": receipt.get("nondet_disagree"),
    }


def balance_of(address):
    try:
        return int(get_json(EXPLORER + "/api/address/" + address).get("balance", 0))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return 0
        raise


def main():
    load_dotenv(ROOT / ".env")
    key = os.environ.get("GENLAYER_PRIVATE_KEY", "")
    if not key:
        print("GENLAYER_PRIVATE_KEY missing; aborting.")
        return 2
    commit = os.environ.get("MILESTONE_COMMIT", "")
    if len(sys.argv) > 1:
        commit = sys.argv[1]
    if not commit:
        import subprocess

        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
    evidence_url = (
        "https://raw.githubusercontent.com/hoveiser/fairpay/" + commit + "/docs/milestone-evidence.txt"
    )
    print("contract commit:", commit)
    print("evidence URL:", evidence_url)

    # Fail early if the evidence file is not publicly reachable at that commit.
    try:
        probe = urllib.request.urlopen(
            urllib.request.Request(evidence_url, headers={"User-Agent": "qoder-agent"}),
            timeout=60,
        )
        if probe.status != 200:
            raise RuntimeError("evidence URL status " + str(probe.status))
    except Exception as exc:
        print("evidence URL is not reachable; push the commit first:", exc)
        return 3

    deploy = json.load(open(EVIDENCE / "deploy.json", encoding="utf-8"))
    contract = deploy["contract_address"]
    employer = create_account(key)
    worker_key = generate_private_key()
    worker = create_account(worker_key)

    print("contract:", contract)
    print("employer:", employer.address, "native balance:", balance_of(employer.address))
    print("worker:", worker.address)

    client = create_client(chain=studionet, account=employer)
    record = {
        "network": "studionet (chain id 61999)",
        "contract": contract,
        "deployed_commit": commit,
        "employer": employer.address,
        "worker": worker.address,
        "evidence_url": evidence_url,
        "params": {
            "base_pay": str(BASE),
            "bonus_cap": str(BONUS),
            "max_liability": str(MAX_LIABILITY),
            "appeal_window_sec": APPEAL_WINDOW,
            "appeal_bond": str(BOND),
            "deposit": str(DEPOSIT),
            "worker_funding": str(WORKER_FUNDING),
        },
        "txs": {},
        "guard_reverts": [],
        "checks": {},
    }

    def write(name, fn, args, account=None, value=0):
        acct = account or employer
        txid = client.write_contract(contract, fn, args=args, account=acct, value=value)
        tx = wait_finalized(txid, name)
        er, _res = execution_result(tx)
        ok = str(er).upper() in ("SUCCESS", "OK", "1")
        cons = consensus_summary(tx)
        print("  {:<28s} {:<34s} tx={} exec={} consensus={} ({}/{})".format(
            name, fn, txid[:12], er, cons["status"], cons["agree"], cons["total"]))
        if not ok:
            print("    revert:", error_text(tx)[:180])
        return txid, tx, ok, cons

    def read(fn, args):
        return client.read_contract(contract, fn, args=args)

    def agreement(aid):
        return json.loads(read("get_agreement", [aid]))

    def tranche(aid, idx=0):
        return json.loads(read("get_tranche", [aid, idx]))

    def latest_agreement():
        count = int(read("get_agreement_count", []))
        return count

    print("\n[1] employer deposits native GEN and mints FPT")
    txid, tx, ok, cons = write("01_deposit", "faucet_or_deposit", [], value=DEPOSIT)
    record["txs"]["deposit"] = {"tx": txid, "ok": ok, "consensus": cons}
    record["employer_fpt_after_deposit"] = int(read("token_balance", [employer.address]))
    record["checks"]["deposit_minted_fpt"] = bool(ok) and record["employer_fpt_after_deposit"] == DEPOSIT
    if not ok:
        print("deposit failed; aborting")
        (EVIDENCE / "milestone_scenario.json").write_text(json.dumps(record, indent=2))
        return 4

    print("\n[2] employer funds the worker appeal bond")
    txid, tx, ok, cons = write("02_transfer_bond", "transfer_tokens", [worker.address, WORKER_FUNDING])
    record["txs"]["transfer_bond"] = {"tx": txid, "ok": ok, "consensus": cons}
    record["worker_fpt_after_funding"] = int(read("token_balance", [worker.address]))
    record["checks"]["worker_funded"] = bool(ok) and record["worker_fpt_after_funding"] == WORKER_FUNDING

    print("\n[3] create agreement 1 (80 GEN locked)")
    txid, tx, ok, cons = write(
        "03_create_a1", "create_payroll_agreement",
        [worker.address, ROLE, RUBRIC, BASE, BONUS, APPEAL_WINDOW, BOND, 1],
    )
    record["txs"]["create_a1"] = {"tx": txid, "ok": ok, "consensus": cons}
    a1 = latest_agreement()
    record["agreement_1"] = a1
    agreement_1 = agreement(a1)
    vault_state_1 = json.loads(read("get_vault_state", []))
    record["checks"]["agreement_1_locked"] = (
        bool(ok) and agreement_1["locked_amount"] == str(MAX_LIABILITY)
        and int(vault_state_1["vault_custody_balance"]) >= MAX_LIABILITY
    )
    print("    agreement 1:", a1, "status:", agreement_1["status"], "locked:", agreement_1["locked_amount"])

    print("\n[4] worker submits the milestone deliverable")
    txid, tx, ok, cons = write(
        "04_submit_a1", "submit_tranche",
        [a1, 0, 40, TIMESHEET, json.dumps([evidence_url])], account=worker,
    )
    record["txs"]["submit_a1"] = {"tx": txid, "ok": ok, "consensus": cons}
    record["checks"]["submission_sealed"] = bool(ok) and tranche(a1, 0)["status"] == "submitted"
    if not ok:
        print("submission failed; aborting")
        (EVIDENCE / "milestone_scenario.json").write_text(json.dumps(record, indent=2))
        return 5

    print("\n[5] live consensus audit")
    audit_ok = False
    for attempt in range(1, 4):
        txid, tx, ok, cons = write("05_audit_a1_r" + str(attempt), "audit_work_period_live", [a1, 0])
        record["txs"]["audit_a1"] = {"tx": txid, "ok": ok, "consensus": cons}
        if ok:
            audit_ok = True
            break
        print("    audit attempt", attempt, "did not finalize a decision; retrying")
        time.sleep(5)
    t1 = tranche(a1, 0)
    record["agreement_1_after_audit"] = agreement(a1)
    record["tranche_1"] = t1
    record["audit"] = {
        "ok": audit_ok,
        "payroll_band": t1.get("payroll_band"),
        "delivery_anchor": t1.get("delivery_anchor"),
        "evidence_authenticated": t1.get("evidence_authenticated"),
        "delivery_score": t1.get("delivery_score"),
        "worker_payout": t1.get("worker_payout"),
        "consensus": record["txs"]["audit_a1"]["consensus"],
        "finalized": record["txs"]["audit_a1"]["consensus"]["status"] == "MAJORITY_AGREE",
    }
    record["checks"]["audit_finalized_majority"] = (
        audit_ok and record["audit"]["consensus"]["status"] == "MAJORITY_AGREE"
        and t1.get("status") == "audited"
    )
    print("    band:", t1.get("payroll_band"), "anchor:", t1.get("delivery_anchor"),
          "payout:", int(t1.get("worker_payout", "0")) // GEN, "GEN")

    print("\n[6] expected guard revert: premature surplus recovery")
    txid, tx, ok, cons = write("06_recover_premature", "recover_employer_surplus", [a1])
    message = error_text(tx)
    record["txs"]["recover_premature"] = {"tx": txid, "ok": ok, "consensus": cons}
    guard_ok = (not ok) and "Appeal window open" in message
    record["guard_reverts"].append({
        "name": "premature employer surplus withdrawal",
        "tx": txid,
        "execution_result": execution_result(tx)[0],
        "error": message,
        "expected": "Appeal window open: liability locked",
        "matched": guard_ok,
        "consensus": cons,
    })
    record["checks"]["premature_recovery_reverted"] = guard_ok

    print("\n[7] agreement 2: single-party proposal does not move funds")
    txid, tx, ok, cons = write(
        "07_create_a2", "create_payroll_agreement",
        [worker.address, ROLE, RUBRIC, 24 * GEN, 6 * GEN, APPEAL_WINDOW, GEN, 1],
    )
    record["txs"]["create_a2"] = {"tx": txid, "ok": ok, "consensus": cons}
    a2 = latest_agreement()
    record["agreement_2"] = a2
    vault_before = json.loads(read("get_vault_state", []))["vault_custody_balance"]
    txid, tx, ok, cons = write("08_mutual_single", "propose_mutual_payroll_settlement", [a2, 7000])
    agreement_2 = agreement(a2)
    vault_after = json.loads(read("get_vault_state", []))["vault_custody_balance"]
    record["txs"]["mutual_single"] = {"tx": txid, "ok": ok, "consensus": cons}
    record["mutual_single"] = {
        "status": agreement_2["status"],
        "employer_signed": agreement_2["mutual"]["employer_signed"],
        "worker_signed": agreement_2["mutual"]["worker_signed"],
        "vault_before": vault_before,
        "vault_after": vault_after,
    }
    record["checks"]["single_party_does_not_settle"] = (
        bool(ok) and agreement_2["status"] != "SETTLED" and vault_before == vault_after
    )

    print("\n[8] matching co-sign settles at 7000 bps")
    txid, tx, ok, cons = write(
        "09_mutual_match", "propose_mutual_payroll_settlement", [a2, 7000], account=worker,
    )
    agreement_2 = agreement(a2)
    record["txs"]["mutual_match"] = {"tx": txid, "ok": ok, "consensus": cons}
    receipt_2 = json.loads(read("get_settlement_receipt", [int(agreement_2["receipt_id"])])) if agreement_2.get("receipt_id") else {}
    record["mutual_settlement"] = {
        "status": agreement_2["status"],
        "receipt": receipt_2,
        "expected_payout": str((24 * GEN + 6 * GEN) * 7000 // 10000),
    }
    record["checks"]["matching_cosign_settles"] = (
        bool(ok) and agreement_2["status"] == "SETTLED"
        and int(receipt_2.get("worker_payout", "0")) + int(receipt_2.get("employer_refund", "0")) == 30 * GEN
    )
    print("    receipt:", receipt_2.get("worker_payout"), "worker,", receipt_2.get("employer_refund"), "refund")

    print("\n[9] expected guard revert: post-settlement mutation")
    txid, tx, ok, cons = write(
        "10_mutual_after_settle", "propose_mutual_payroll_settlement", [a2, 5000], account=worker,
    )
    message = error_text(tx)
    record["txs"]["mutual_after_settle"] = {"tx": txid, "ok": ok, "consensus": cons}
    guard_ok = (not ok) and "already settled" in message
    record["guard_reverts"].append({
        "name": "post-settlement mutation",
        "tx": txid,
        "execution_result": execution_result(tx)[0],
        "error": message,
        "expected": "Agreement already settled",
        "matched": guard_ok,
        "consensus": cons,
    })
    record["checks"]["post_settlement_mutation_reverted"] = guard_ok

    print("\n[10] agreement 3: co-sign bps mismatch reverts")
    txid, tx, ok, cons = write(
        "11_create_a3", "create_payroll_agreement",
        [worker.address, ROLE, RUBRIC, 24 * GEN, 6 * GEN, APPEAL_WINDOW, GEN, 1],
    )
    record["txs"]["create_a3"] = {"tx": txid, "ok": ok, "consensus": cons}
    a3 = latest_agreement()
    record["agreement_3"] = a3
    txid, tx, ok, cons = write("12_mutual_a3_employer", "propose_mutual_payroll_settlement", [a3, 6000])
    record["txs"]["mutual_a3_employer"] = {"tx": txid, "ok": ok, "consensus": cons}
    txid, tx, ok, cons = write(
        "13_mutual_a3_mismatch", "propose_mutual_payroll_settlement", [a3, 7000], account=worker,
    )
    message = error_text(tx)
    record["txs"]["mutual_a3_mismatch"] = {"tx": txid, "ok": ok, "consensus": cons}
    guard_ok = (not ok) and "Co-sign bps mismatch" in message
    record["guard_reverts"].append({
        "name": "single-party co-sign bps mismatch",
        "tx": txid,
        "execution_result": execution_result(tx)[0],
        "error": message,
        "expected": "Co-sign bps mismatch",
        "matched": guard_ok,
        "consensus": cons,
    })
    record["checks"]["cosign_mismatch_reverted"] = guard_ok
    # Match the standing 6000 proposal so agreement 3 settles and its funds leave custody.
    txid, tx, ok, cons = write(
        "14_mutual_a3_match", "propose_mutual_payroll_settlement", [a3, 6000], account=worker,
    )
    record["txs"]["mutual_a3_match"] = {"tx": txid, "ok": ok, "consensus": cons}
    record["checks"]["mismatch_then_match_settles"] = bool(ok) and agreement(a3)["status"] == "SETTLED"

    print("\n[11] worker appeals agreement 1 and posts the bond")
    txid, tx, ok, cons = write("15_appeal_a1", "appeal_tranche", [a1, 0], account=worker)
    record["txs"]["appeal_a1"] = {"tx": txid, "ok": ok, "consensus": cons}
    t1 = tranche(a1, 0)
    record["appeal"] = {
        "status": t1["status"],
        "bond_posted": t1["appeal_bond_posted"],
        "worker_fpt_after_bond": int(read("token_balance", [worker.address])),
    }
    record["checks"]["appeal_accepted"] = bool(ok) and t1["status"] == "appealed"

    print("\n[12] live appeal resolution")
    resolve_ok = False
    for attempt in range(1, 4):
        txid, tx, ok, cons = write("16_resolve_a1_r" + str(attempt), "resolve_appeal_live", [a1, 0])
        record["txs"]["resolve_a1"] = {"tx": txid, "ok": ok, "consensus": cons}
        if ok:
            resolve_ok = True
            break
        time.sleep(5)
    t1 = tranche(a1, 0)
    record["appeal_resolution"] = {
        "ok": resolve_ok,
        "payroll_band": t1.get("payroll_band"),
        "delivery_anchor": t1.get("delivery_anchor"),
        "worker_payout": t1.get("worker_payout"),
        "bond_outcome": t1.get("bond_outcome"),
        "appeal_resolved": t1.get("appeal_resolved"),
        "consensus": record["txs"]["resolve_a1"]["consensus"],
    }
    record["checks"]["appeal_resolved_by_consensus"] = (
        resolve_ok and bool(t1.get("appeal_resolved"))
        and record["txs"]["resolve_a1"]["consensus"]["status"] == "MAJORITY_AGREE"
    )
    print("    final anchor:", t1.get("delivery_anchor"), "bond:", t1.get("bond_outcome"))

    print("\n[13] settle agreement 1 and execute the payout claim")
    worker_before = int(read("token_balance", [worker.address]))
    txid, tx, ok, cons = write("17_settle_a1", "settle_agreement", [a1])
    agreement_1 = agreement(a1)
    receipt_1 = json.loads(read("get_settlement_receipt", [int(agreement_1["receipt_id"])])) if agreement_1.get("receipt_id") else {}
    worker_after = int(read("token_balance", [worker.address]))
    record["txs"]["settle_a1"] = {"tx": txid, "ok": ok, "consensus": cons}
    record["settlement"] = {
        "status": agreement_1["status"],
        "receipt": receipt_1,
        "worker_fpt_before": worker_before,
        "worker_fpt_after": worker_after,
        "delta": worker_after - worker_before,
    }
    record["checks"]["payout_matches_receipt"] = (
        bool(ok) and agreement_1["status"] == "SETTLED"
        and worker_after - worker_before == int(receipt_1.get("worker_payout", "0"))
    )
    print("    receipt:", receipt_1.get("worker_payout"), "payout,", receipt_1.get("employer_refund"), "refund")

    print("\n[14] worker transfer_tokens after settlement")
    before_employer = int(read("token_balance", [employer.address]))
    before_worker = int(read("token_balance", [worker.address]))
    txid, tx, ok, cons = write("18_transfer_tokens", "transfer_tokens", [employer.address, GEN], account=worker)
    record["txs"]["transfer_tokens"] = {"tx": txid, "ok": ok, "consensus": cons}
    after_employer = int(read("token_balance", [employer.address]))
    after_worker = int(read("token_balance", [worker.address]))
    record["token_transfer"] = {
        "amount": str(GEN),
        "worker_before": before_worker,
        "worker_after": after_worker,
        "employer_before": before_employer,
        "employer_after": after_employer,
    }
    record["checks"]["transfer_tokens_moved_exactly"] = (
        bool(ok) and before_worker - after_worker == GEN and after_employer - before_employer == GEN
    )

    print("\n[15] vault invariant and final state")
    state = json.loads(read("get_vault_state", []))
    invariant = read("check_vault_invariants", [])
    record["vault_state"] = state
    record["check_vault_invariants"] = bool(invariant)
    record["checks"]["vault_invariant_holds"] = (
        bool(invariant) and state.get("invariant_holds") is True
        and state.get("vault_custody_balance") == state.get("locked_payroll_escrows")
        and state.get("active_appeal_bonds") == "0"
    )
    record["final_fpt_balances"] = {
        "employer": int(read("token_balance", [employer.address])),
        "worker": int(read("token_balance", [worker.address])),
    }

    record["guard_revert_count"] = len([g for g in record["guard_reverts"] if g["matched"]])
    record["checks"]["three_guard_reverts_matched"] = record["guard_revert_count"] >= 3
    record["all_checks_passed"] = all(record["checks"].values())
    (EVIDENCE / "milestone_scenario.json").write_text(json.dumps(record, indent=2), encoding="utf-8")

    print("\n=== SUMMARY ===")
    print(json.dumps({
        "contract": contract,
        "audit": record["audit"],
        "guard_reverts": record["guard_reverts"],
        "mutual": record["mutual_settlement"],
        "settlement": record["settlement"],
        "checks": record["checks"],
        "all_checks_passed": record["all_checks_passed"],
    }, indent=2))
    return 0 if record["all_checks_passed"] else 6


if __name__ == "__main__":
    sys.exit(main())
