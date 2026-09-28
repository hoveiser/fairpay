# FairPay Direct Mode test harness (GenLayer Testing Suite / gltest VMContext).
#
# This harness uses the ACTUAL installed direct-mode API (gltest 0.29.2), which
# runs the contract inside the pinned GenVM runner declared by the contract
# header (py-genlayer:1jb45aa8...). Empirically verified against the installed
# SDK:
#   * direct_vm.sender / direct_vm.value drive gl.message.sender_address / value.
#   * The contract's clock reads gl.message_raw["datetime"]; direct_vm.warp() does
#     NOT refresh that dict for the contract, so we set it directly via `set_time`.
#   * The VM does not natively simulate native-value transfers (EthSend), so we
#     install a gl_call hook that records EthSend payloads and fund the contract
#     balance via direct_vm.deal() so payout asserts pass.
import json
import datetime as _dt

import pytest

GEN = 10**18

EVIDENCE_V1 = "proof of work version 1 - deployed feature with tests and docs, real impact"
EVIDENCE_V2 = "proof of work version 2 - MUTATED after submission to inflate the audit"

IPFS_GOOD = "https://ipfs.io/ipfs/bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi"
IPFS_DEAD = "https://ipfs.io/ipfs/bafybeihkoviema7g3gxyt6la7vd5ho32ictqbilu3wnlo3rs7ewhnp7lly"

ITEMS = json.dumps([{"desc": "built feature", "url": IPFS_GOOD, "impact": "works"}])
DEAD_ITEMS = json.dumps([{"desc": "built feature", "url": IPFS_DEAD, "impact": "works"}])

# default create_job parameters that satisfy the validated bounds
DEFAULT_ROLE = "dev"
DEFAULT_RUBRIC = "work must be real and substantial"
DEFAULT_RATE = 1
DEFAULT_APPEAL_WINDOW = 120
DEFAULT_MAX_HOURS = 40
DEFAULT_STALE_WINDOW = 3600


def addr(value):
    """Normalize a gltest address (20-byte value or hex string) to a hex string."""
    if isinstance(value, (bytes, bytearray)):
        return "0x" + bytes(value).hex()
    return str(value)


def _epoch(ts):
    return int(_dt.datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp())


def iso(epoch):
    """Format a unix epoch (int) back into the contract's Z-suffixed ISO clock."""
    return _dt.datetime.fromtimestamp(epoch, _dt.timezone.utc).isoformat().replace("+00:00", "Z")


def _ceil_max(hours, rate):
    """Independent re-implementation of the contract's ceiling max liability."""
    return -(-(hours * rate * 125 * 10**18) // 100)


class Controller:
    def __init__(self, vm, gl, c, sends):
        self.vm = vm
        self.gl = gl
        self.c = c
        self.sends = sends

    # ---- time -------------------------------------------------------------
    def set_time(self, ts):
        self.gl.message_raw["datetime"] = ts

    def add_time(self, seconds):
        self.gl.message_raw["datetime"] = iso(self.now() + seconds)

    def now(self):
        return _epoch(self.gl.message_raw["datetime"])

    # ---- reads ------------------------------------------------------------
    def job(self, job_id):
        return json.loads(self.c.get_job(job_id))

    def period(self, period_id):
        return json.loads(self.c.get_period(period_id))

    def balance(self, job_id):
        return self.job(job_id)["budget"]

    # ---- independent oracle (used by many tests) --------------------------
    def expected_reserve(self, job_id):
        """Sum of the MAXIMUM payout still reachable across all periods.

        Recomputed here independently of the contract so the reserved-liability
        invariant (budget >= this) is checked against a test-owned oracle rather
        than the contract's own view. finalize() can therefore never fail with
        'Job budget insufficient' for a reason attributable to recovery.
        """
        job = self.job(job_id)
        now = self.now()
        total = 0
        for pid in job["period_ids"]:
            p = self.period(int(pid))
            st = p["status"]
            if st in ("submitted", "disputed"):
                total += _ceil_max(p["hours"], job["rate"])
            elif st == "adjudicated":
                appeal_possible = (
                    p["appeals_used"] == 0
                    and now < p["adjudicated_at"] + job["appeal_window_sec"]
                )
                total += _ceil_max(p["hours"], job["rate"]) if appeal_possible else p["pay"]
            # paid / dismissed / unresolvable contribute nothing
        return total

    def assert_invariant(self, job_id):
        assert self.balance(job_id) >= self.expected_reserve(job_id), (
            "Invariant violated: budget no longer covers the maximum reachable payout"
        )

    # ---- contract's own view (to compare against the oracle) --------------
    def reserved(self, job_id):
        return self.c.reserved_liability(job_id)

    # ---- actions ----------------------------------------------------------
    def create_job(self, employer, worker, budget=10 * GEN, rate=DEFAULT_RATE,
                   appeal_window=DEFAULT_APPEAL_WINDOW, max_hours=DEFAULT_MAX_HOURS,
                   stale_window=DEFAULT_STALE_WINDOW, role=DEFAULT_ROLE,
                   rubric=DEFAULT_RUBRIC):
        self.vm.sender = employer
        self.vm.value = budget
        jid = self.c.create_job(worker, role, rubric, rate, appeal_window, max_hours, stale_window)
        self.vm.value = 0
        return jid

    def submit(self, worker, job_id, hours, items=ITEMS):
        self.vm.sender = worker
        return self.c.submit_period(job_id, hours, items)

    def resolve(self, period_id):
        return self.c.resolve_period(period_id)

    def appeal(self, period_id, actor):
        self.vm.sender = actor
        return self.c.appeal(period_id)

    def finalize(self, period_id, actor):
        self.vm.sender = actor
        return self.c.finalize(period_id)

    def recover(self, employer, job_id):
        self.vm.sender = employer
        return self.c.recover_budget(job_id)

    def dismiss_stale(self, employer, period_id):
        self.vm.sender = employer
        return self.c.dismiss_stale(period_id)

    def dismiss(self, employer, period_id):
        self.vm.sender = employer
        return self.c.dismiss(period_id)

    def top_up(self, employer, job_id, amount):
        self.vm.sender = employer
        self.vm.value = amount
        r = self.c.top_up(job_id)
        self.vm.value = 0
        return r

    # ---- mocks ------------------------------------------------------------
    def mock_evidence(self, body, status=200, pattern=r"ipfs\.io"):
        self.vm.mock_web(pattern, {"status": status, "body": body})

    def mock_tier(self, tier, reasoning="verified against the rubric"):
        # gltest appends mocks and the matcher returns the FIRST regex hit, so a
        # re-registered r".*" would never take effect. Replace the LLM mock list
        # in place (leaving web mocks intact) so the latest tier wins.
        self.vm._llm_mocks.clear()
        self.vm.mock_llm(r".*", json.dumps({"tier": tier, "reasoning": reasoning}))


@pytest.fixture
def fp(direct_vm, direct_deploy):
    """Deploy a funded FairPay with EthSend capture and time control."""

    def _factory(budget=10 * GEN, employer_balance=1_000_000 * GEN):
        sends = []

        def hook(v, request):
            if isinstance(request, dict) and "EthSend" in request:
                sends.append(request["EthSend"])
                return {"ok": None}
            return None

        c = direct_deploy("contracts/contract.py")
        import genlayer.gl as gl

        direct_vm._gl_call_hook = hook
        direct_vm.deal(direct_vm._contract_address, employer_balance)
        return Controller(direct_vm, gl, c, sends)

    return _factory
