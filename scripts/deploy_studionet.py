#!/usr/bin/env python3
"""Stage A: deploy contracts/contract.py to StudioNet and prove it landed.

- Reads GENLAYER_PRIVATE_KEY from the gitignored .env. The key is never printed,
  logged, or written anywhere.
- Deploys through genlayer-py (the CLI keystore is locked in this environment).
- Waits for the deploy transaction to reach FINALIZED.
- Resolves the contract address from the deploy transaction via the explorer
  JSON API.
- Confirms the source stored on the explorer matches the repo file byte for byte.

Raw API output is saved under evidence/ so nothing is paraphrased.
"""
import json
import os
import sys
import pathlib

from dotenv import load_dotenv

import genlayer_py
from genlayer_py import create_account, create_client, studionet

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONTRACT_FILE = ROOT / "contracts" / "contract.py"
EVIDENCE = ROOT / "evidence"
EVIDENCE.mkdir(exist_ok=True)
EXPLORER = "https://explorer-studio.genlayer.com"

import urllib.request


def explorer_finalized_by_account(address: str, tx_hash: str, timeout_s: int = 600) -> dict:
    """Deploys are not served by the single-transaction explorer route, so poll
    the account transaction list until the deploy shows FINALIZED, then return
    its raw record (which carries the created contract address)."""
    import time
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            url = f"{EXPLORER}/api/transactions?address={address}"
            req = urllib.request.Request(url, headers={"User-Agent": "qoder-agent"})
            txs = json.load(urllib.request.urlopen(req, timeout=60))["transactions"]
            for t in txs:
                if t["hash"].lower() == tx_hash.lower() and t.get("status") == "FINALIZED":
                    return t
        except Exception:
            pass
        time.sleep(6)
    raise RuntimeError(f"deploy {tx_hash} not FINALIZED on explorer within {timeout_s}s")


def main() -> int:
    load_dotenv(ROOT / ".env")
    key = os.environ.get("GENLAYER_PRIVATE_KEY", "")
    if not key:
        print("GENLAYER_PRIVATE_KEY missing from .env; aborting.")
        return 2
    employer = create_account(key)
    print("employer address:", employer.address)

    client = create_client(chain=studionet, account=employer)

    source_bytes = CONTRACT_FILE.read_bytes()
    # Deploy the exact repo bytes so the explorer copy can be byte-matched.
    code = source_bytes.decode("utf-8")

    print("submitting deploy transaction ...")
    deploy_txid = client.deploy_contract(code=code)
    print("deploy consensus txid:", deploy_txid)

    # Deploys are not readable via eth_getTransactionByHash or the single-tx
    # explorer route on StudioNet, so resolve the FINALIZED deploy record (and
    # the created contract) from the account transaction list on the explorer.
    tx = explorer_finalized_by_account(employer.address, deploy_txid)
    (EVIDENCE / "deploy_explorer_tx.json").write_text(json.dumps(tx, indent=2))
    contract = (tx.get("data") or {}).get("contract_address") or tx.get("to_address")
    print("deploy tx status:", tx.get("status"))
    print("resolved contract address:", contract)
    if not contract:
        print("could not resolve contract address; inspect evidence/deploy_explorer_tx.json")
        return 3

    # Byte-match: fetch stored source over RPC gen_getContractCode and compare.
    import base64
    payload = json.dumps(
        {"jsonrpc": "2.0", "id": 1, "method": "gen_getContractCode", "params": [contract]}
    ).encode()
    req = urllib.request.Request(
        "https://studio.genlayer.com/api",
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "qoder-agent"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        stored_b64 = json.load(r)["result"]
    stored_bytes = base64.b64decode(stored_b64)
    (EVIDENCE / "stored_source.bin").write_bytes(stored_bytes)
    match = stored_bytes == source_bytes
    print("byte-match stored source vs repo file:", match,
          f"(stored {len(stored_bytes)} bytes, repo {len(source_bytes)} bytes)")

    (EVIDENCE / "deploy.json").write_text(json.dumps({
        "network": "studionet (chain id 61999)",
        "employer": employer.address,
        "deploy_txid": deploy_txid,
        "contract_address": contract,
        "source_byte_match": match,
    }, indent=2))
    print("\nOK ->", contract)
    return 0 if match else 4


if __name__ == "__main__":
    sys.exit(main())
