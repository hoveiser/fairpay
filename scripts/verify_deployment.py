#!/usr/bin/env python3
"""Verify the deployed FairPay contract is byte-identical to the local source.

Reads the contract address from evidence/deploy.json (or an optional CLI arg),
fetches the source stored on-chain via the JSON-RPC method `gen_getContractCode`
against the StudioNet endpoint, base64-decodes it, and compares it byte for byte
with contracts/contract.py. It also reads the pinned runner header so a reviewer
can confirm the version. Nothing is deployed or written except the raw stored
source and a small JSON result under evidence/. The key is never used or needed.

Usage:
    python scripts/verify_deployment.py [contract_address]
Exit code 0 only when byte_match is true.
"""
import base64
import json
import pathlib
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONTRACT_FILE = ROOT / "contracts" / "contract.py"
EVIDENCE = ROOT / "evidence"
RPC = "https://studio.genlayer.com/api"
EXPLORER = "https://explorer-studio.genlayer.com"


def get_contract_code(address: str) -> bytes:
    payload = json.dumps(
        {"jsonrpc": "2.0", "id": 1, "method": "gen_getContractCode", "params": [address]}
    ).encode()
    req = urllib.request.Request(
        RPC, data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "qoder-agent"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        resp = json.load(r)
    if "error" in resp:
        raise RuntimeError(f"gen_getContractCode error: {resp['error']}")
    return base64.b64decode(resp["result"])


def main() -> int:
    if len(sys.argv) > 1:
        address = sys.argv[1]
    else:
        address = json.loads((EVIDENCE / "deploy.json").read_text())["contract_address"]

    source_bytes = CONTRACT_FILE.read_bytes()
    first_line = source_bytes.split(b"\n", 1)[0].decode("utf-8", "ignore")
    print(f"contract address : {address}")
    print(f"explorer         : {EXPLORER}/address/{address}")
    print(f"local source     : {CONTRACT_FILE} ({len(source_bytes)} bytes)")
    print(f"local header     : {first_line}")

    stored_bytes = get_contract_code(address)
    EVIDENCE.mkdir(exist_ok=True)
    (EVIDENCE / "stored_source.bin").write_bytes(stored_bytes)
    match = stored_bytes == source_bytes
    print(f"stored source    : {len(stored_bytes)} bytes (fetched via gen_getContractCode)")
    print(f"byte_match       : {match}")

    result = {
        "contract_address": address,
        "explorer": f"{EXPLORER}/address/{address}",
        "network": "studionet (chain id 61999)",
        "local_bytes": len(source_bytes),
        "stored_bytes": len(stored_bytes),
        "byte_match": match,
        "rpc_method": "gen_getContractCode",
        "rpc_endpoint": RPC,
    }
    (EVIDENCE / "deployment_verification.json").write_text(json.dumps(result, indent=2))

    if not match:
        print("MISMATCH: deployed source differs from contracts/contract.py")
        return 1
    print("OK: deployed contract source is byte-identical to the repo file")
    return 0


if __name__ == "__main__":
    sys.exit(main())
