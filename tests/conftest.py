# FairPay Milestone v1 Direct Mode harness (gltest 0.29.2, pinned runner).
#
# The contract runs inside the actual runner declared by its header. This file
# adds the pieces Direct Mode does not provide by itself:
#   * a controllable clock (the contract reads gl.message_raw["datetime"]),
#   * web mocks for gl.nondet.web.render and LLM mocks for exec_prompt,
#   * a deterministic stand-in for the EqComparative LLM judge used by
#     prompt_comparative, which compares the three consensus fields exactly.
import ast
import datetime as _dt
import json
import re

import pytest

GEN = 10**18

T0 = "2026-10-21T12:00:00Z"
WINDOW = 120
BASE = 60 * GEN
BONUS = 20 * GEN
MAX_LIABILITY = BASE + BONUS
BOND = 2 * GEN
DEPOSIT = 200 * GEN
TRANCHE_COUNT = 1

BAND_FULL = "FULL_BONUS_PAYOUT"
BAND_STANDARD = "STANDARD_TARGET_PAYOUT"
BAND_PARTIAL = "PARTIAL_PRORATED_PAYOUT"
BAND_REJECTED = "REJECTED_NON_DELIVERY"

COMMIT = "a" * 40
GOOD_URL = "https://raw.githubusercontent.com/hoveiser/fairpay/" + COMMIT + "/docs/milestone-evidence.txt"
IPFS_URL = "https://ipfs.io/ipfs/bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi"

EVIDENCE_OK = (
    "FairPay Milestone v1 delivery note. The funded FPT vault locks the full "
    "maximum liability for every payroll agreement. Two-party mutual settlement "
    "requires matching employer and worker signatures. The consensus audit "
    "quantizes delivery onto the 0, 50, 80, 100 anchor ladder and verifies every "
    "settlement with a discrete payroll band. Tests cover the PAPITO lock, the "
    "co-sign guard, and the vault invariant."
)
EVIDENCE_MUTATED = EVIDENCE_OK + " MUTATED AFTER SUBMISSION."


def addr(value):
    if isinstance(value, (bytes, bytearray)):
        return "0x" + bytes(value).hex()
    return str(value)


def _epoch(ts):
    return int(_dt.datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp())


def iso(epoch):
    return _dt.datetime.fromtimestamp(epoch, _dt.timezone.utc).isoformat().replace("+00:00", "Z")


def _fields(answer):
    """Extract the three consensus fields from a formatted calldata answer."""
    text = str(answer)
    try:
        obj = ast.literal_eval(text)
        if isinstance(obj, dict):
            return {k: obj.get(k) for k in ("payroll_band", "delivery_anchor", "evidence_authenticated")}
    except Exception:
        pass
    out = {}
    for key in ("payroll_band", "delivery_anchor", "evidence_authenticated"):
        m = re.search(
            r"['\"]?" + key + r"['\"]?\s*:\s*(['\"]?)([^,'\"}\s]+)\1",
            text,
        )
        if m is None:
            return None
        out[key] = m.group(2)
    return out


class Controller:
    def __init__(self, vm, gl, contract, sends, comparisons):
        self.vm = vm
        self.gl = gl
        self.c = contract
        self.sends = sends
        self.comparisons = comparisons

    # ---- clock ------------------------------------------------------------
    def set_time(self, ts):
        self.gl.message_raw["datetime"] = ts

    def add_time(self, seconds):
        self.set_time(iso(self.now() + int(seconds)))

    def now(self):
        return _epoch(self.gl.message_raw["datetime"])

    # ---- reads ------------------------------------------------------------
    def agreement(self, aid):
        return json.loads(self.c.get_agreement(aid))

    def tranche(self, aid, idx=0):
        return json.loads(self.c.get_tranche(aid, idx))

    def receipt(self, rid):
        return json.loads(self.c.get_settlement_receipt(rid))

    def balance(self, who):
        return self.c.token_balance(addr(who))

    def vault_state(self):
        return json.loads(self.c.get_vault_state())

    def reserved(self, aid):
        return self.c.reserved_liability(aid)

    def invariant(self):
        return self.c.check_vault_invariants()

    # ---- ledger -----------------------------------------------------------
    def deposit(self, who, amount=DEPOSIT):
        self.vm.sender = who
        self.vm.value = amount
        self.c.faucet_or_deposit()
        self.vm.value = 0

    def transfer(self, sender, to, amount):
        self.vm.sender = sender
        self.c.transfer_tokens(addr(to), amount)

    # ---- agreement lifecycle ---------------------------------------------
    def create(self, employer, worker, base=BASE, bonus=BONUS, window=WINDOW,
               bond=BOND, tranches=TRANCHE_COUNT, role="release engineer",
               rubric="deliver a real release note with tests and evidence"):
        self.vm.sender = employer
        return self.c.create_payroll_agreement(
            addr(worker), role, rubric, base, bonus, window, bond, tranches
        )

    def submit(self, worker, aid, idx=0, hours=40, urls=None):
        self.vm.sender = worker
        if urls is None:
            urls = [GOOD_URL]
        return self.c.submit_tranche(aid, idx, hours, EVIDENCE_OK, json.dumps(urls))

    def audit(self, aid, idx=0, actor=None):
        if actor is not None:
            self.vm.sender = actor
        return self.c.audit_work_period_live(aid, idx)

    def appeal(self, worker, aid, idx=0):
        self.vm.sender = worker
        return self.c.appeal_tranche(aid, idx)

    def resolve_appeal(self, aid, idx=0):
        return self.c.resolve_appeal_live(aid, idx)

    def mutual(self, actor, aid, bps):
        self.vm.sender = actor
        return self.c.propose_mutual_payroll_settlement(aid, bps)

    def settle(self, aid, actor=None):
        if actor is not None:
            self.vm.sender = actor
        return self.c.settle_agreement(aid)

    def recover(self, employer, aid):
        self.vm.sender = employer
        return self.c.recover_employer_surplus(aid)

    # ---- mocks ------------------------------------------------------------
    def mock_evidence(self, body=EVIDENCE_OK, status=200, pattern=None):
        if pattern is None:
            pattern = r"raw\.githubusercontent\.com"
        # Replace, do not append: the matcher returns the first hit, so a stale
        # mock would otherwise hide a mutation or an unreachable-page scenario.
        self.vm._web_mocks.clear()
        self.vm.mock_web(pattern, {"status": status, "body": body})

    def mock_audit(self, authenticated=True, score=80, reasoning="verified against the rubric"):
        payload = {
            "evidence_authenticated": authenticated,
            "delivery_score": score,
            "reasoning": reasoning,
        }
        self.vm._llm_mocks.clear()
        self.vm.mock_llm(r".*", json.dumps(payload))

    def mock_raw_llm(self, raw):
        self.vm._llm_mocks.clear()
        self.vm.mock_llm(r".*", str(raw))

    def run_validator(self):
        return self.vm.run_validator()


def _install_hook(direct_vm, sends, comparisons):
    def hook(vm, request):
        if isinstance(request, dict) and "ExecPromptTemplate" in request:
            payload = request["ExecPromptTemplate"]
            if payload.get("template") != "EqComparative":
                return {"ok": False}
            leader = _fields(payload.get("leader_answer", ""))
            validator = _fields(payload.get("validator_answer", ""))
            keys = ("payroll_band", "delivery_anchor", "evidence_authenticated")
            ok = (
                leader is not None
                and validator is not None
                and all(str(leader.get(k)) == str(validator.get(k)) for k in keys)
            )
            comparisons.append({"leader": leader, "validator": validator, "ok": ok})
            return {"ok": ok}
        if isinstance(request, dict) and "EthSend" in request:
            sends.append(request["EthSend"])
            return {"ok": None}
        return None

    direct_vm._gl_call_hook = hook


@pytest.fixture
def fp(direct_vm, direct_deploy):
    """Deploy a FairPay contract with time control and consensus mocks."""

    def _factory(native_balance=1_000_000 * GEN):
        c = direct_deploy("contracts/contract.py")
        import genlayer.gl as gl

        sends = []
        comparisons = []
        _install_hook(direct_vm, sends, comparisons)
        direct_vm.deal(direct_vm._contract_address, native_balance)
        direct_vm.warp(T0)
        ctrl = Controller(direct_vm, gl, c, sends, comparisons)
        ctrl.set_time(T0)
        return ctrl

    return _factory


@pytest.fixture
def funded(fp, direct_vm, direct_alice, direct_bob):
    """A deployer-funded environment: employer has FPT and the worker has bond FPT."""
    c = fp()
    c.deposit(direct_alice, DEPOSIT)
    c.transfer(direct_alice, direct_bob, BOND)
    return c
