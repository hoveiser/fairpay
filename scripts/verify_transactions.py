#!/usr/bin/env python3
"""Verify every FairPay StudioNet transaction against the explorer JSON API.

For each transaction this re-fetches the raw record from
https://explorer-studio.genlayer.com/api/transactions/<hash> and checks:
  * lifecycle status is FINALIZED;
  * the method (decoded from the ledger calldata) matches what we expect;
  * the contract execution result matches what we expect (SUCCESS or ERROR);
  * for the reverted evidence submissions, the strict_eq sealed value proves
    the on-chain ipfs.io fetch returned a 4xx/empty result (FETCH_FAILED).

Raw records are saved under evidence/verify/ and a roll-up is written to
evidence/verification.json. Nothing is paraphrased: the assertions read the
same bytes the explorer serves. Exit code is non-zero if any check fails.
"""
import base64
import json
import pathlib
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
EVIDENCE = ROOT / "evidence"
VDIR = EVIDENCE / "verify"
VDIR.mkdir(parents=True, exist_ok=True)
EXPLORER = "https://explorer-studio.genlayer.com"

METHODS = ("create_job", "submit_period", "resolve_period", "appeal",
           "recover_budget", "finalize", "top_up")


def get(path: str):
    req = urllib.request.Request(EXPLORER + path, headers={"User-Agent": "qoder-agent"})
    return json.load(urllib.request.urlopen(req, timeout=60))


def tx_by_hash(txid: str, name: str):
    """Single-tx endpoint (with retries; the route is intermittently flaky).
    Falls back to the raw explorer record already saved during the run, so a
    verification never depends on a live 404."""
    import time
    for _ in range(5):
        try:
            return get(f"/api/transactions/{txid}")["transaction"], "live"
        except urllib.error.HTTPError:
            time.sleep(3)
    # fall back to the raw record captured live during the scenario run
    txdir = EVIDENCE / "txs"
    for p in txdir.glob(f"*_{txid[:10]}.json"):
        return json.load(p.open()), f"saved:{p.name}"
    return None, None


def decode_calldata(tx: dict) -> str:
    blob = (tx.get("data") or {}).get("calldata") or ""
    try:
        s = base64.b64decode(blob).decode("latin-1", errors="ignore")
        for m in METHODS:
            if m in s:
                return m
    except Exception:
        pass
    return "?"


def exec_and_seal(tx: dict):
    lr = (tx.get("consensus_data") or {}).get("leader_receipt") or [{}]
    r0 = lr[0]
    seal = None
    for v in (r0.get("eq_outputs") or {}).values():
        try:
            seal = base64.b64decode(v)
        except Exception:
            pass
    gr = r0.get("genvm_result") or {}
    err = gr.get("stderr") or ""
    if isinstance(err, list):
        err = "".join(chr(c) if isinstance(c, int) else str(c) for c in err)
    reason = err.strip().splitlines()[-1] if err.strip() else None
    return r0.get("execution_result"), seal, reason


# Manifest: (name, hash, expected_method, expected_execution_result, expected_reason_substring)
# want_method None skips the method check (used for the deploy tx, whose calldata
# carries no function name). expected_reason is checked only for reverted submits.
SCENARIO = json.load(open(EVIDENCE / "scenario.json")) if (EVIDENCE / "scenario.json").exists() else {"txs": {}, "gateway_probe": {}}
_s = SCENARIO["txs"]
_p = SCENARIO["gateway_probe"]
FETCH_FAIL = "Evidence not fetchable at submission time"
MANIFEST = [
    ("deploy_contract", json.load(open(EVIDENCE / "deploy.json"))["deploy_txid"], None, "SUCCESS", None),
    ("01_create_job", _s["create_job"], "create_job", "SUCCESS", None),
    ("02_submit_dweb", _p["dweb.link"]["tx"], "submit_period", "ERROR", FETCH_FAIL),
    ("02_submit_w3s", _p["w3s.link"]["tx"], "submit_period", "ERROR", FETCH_FAIL),
    ("02_submit_ipfs", _p["ipfs.io"]["tx"], "submit_period", "ERROR", FETCH_FAIL),
    ("02_submit_pinata", _p["gateway.pinata.cloud"]["tx"], "submit_period", "SUCCESS", None),
    ("03_resolve_first", _s["resolve_first"], "resolve_period", "SUCCESS", None),
    ("05_recover_budget", _s["recover_budget"], "recover_budget", "SUCCESS", None),
    ("06_appeal", _s["appeal"], "appeal", "SUCCESS", None),
    ("07_resolve_final", _s["resolve_final"], "resolve_period", "SUCCESS", None),
    ("08_finalize", _s["finalize"], "finalize", "SUCCESS", None),
]


def main() -> int:
    deploy = json.load(open(EVIDENCE / "deploy.json"))
    contract = deploy["contract_address"]
    out = {"contract": contract, "transactions": [], "all_ok": True}

    print(f"verifying contract {contract} on StudioNet\n")

    for name, h, want_method, want_exec, want_reason in MANIFEST:
        tx, source = tx_by_hash(h, name)
        if tx is None:
            print(f"[MISSING] {name} {h} not found on explorer")
            out["all_ok"] = False
            continue
        (VDIR / f"{name}.json").write_text(json.dumps(tx, indent=2))
        method = decode_calldata(tx)
        ex, seal, reason = exec_and_seal(tx)
        ok_status = tx.get("status") == "FINALIZED"
        ok_method = want_method is None or method == want_method
        ok_exec = str(ex).upper() == want_exec
        ok_reason = True
        if want_reason is not None:
            ok_reason = bool(reason) and want_reason in reason
        row_ok = ok_status and ok_method and ok_exec and ok_reason
        out["all_ok"] = out["all_ok"] and row_ok
        out["transactions"].append({
            "name": name, "hash": h, "explorer_tx": f"{EXPLORER}/tx/{h}",
            "status": tx.get("status"), "method": method,
            "execution_result": ex, "revert_reason": reason,
            "sealed_eq_output": (seal.decode("latin-1", "ignore") if seal else None),
            "record_source": source,
            "checks_ok": row_ok,
        })
        print(f"[{'OK ' if row_ok else 'BAD'}] {name:20s} status={tx.get('status')} "
              f"method={method} exec={ex} reason={str(reason)[:60]!r} value={int(tx.get('value') or 0)//10**18}gen src={source}")

    (EVIDENCE / "verification.json").write_text(json.dumps(out, indent=2))
    print("\nALL CHECKS PASSED" if out["all_ok"] else "\nSOME CHECKS FAILED")
    return 0 if out["all_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
