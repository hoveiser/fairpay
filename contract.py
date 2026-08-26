# v0.2.16
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *
import json
import datetime as _dt
import re as _re
import genlayer.gl._internal.gl_call as _glc

MAX_FETCH_FAILURES = 3
MAX_ITEMS = 3

def _clean_text(body: bytes) -> str:
    raw = body.decode("utf-8", errors="ignore")
    raw = _re.sub(r"(?s)<(style|script).*?</\1>", " ", raw)
    text = _re.sub(r"<[^>]+>", " ", raw)
    return _re.sub(r"\s+", " ", text).strip()

def _fetch_all(items) -> str:
    parts = []
    for i, it in enumerate(items):
        response = gl.nondet.web.get(it["url"])
        text = _clean_text(response.body)[:1500]
        parts.append("[Item " + str(i + 1) + ": " + it["desc"] + " | claimed impact: " + it.get("impact", "") + "]\n" + text)
    return "\n\n".join(parts)

class FairPay(gl.Contract):
    jobs: TreeMap[str, str]
    periods: TreeMap[str, str]
    next_job: str
    next_period: str

    def __init__(self):
        self.next_job = "1"
        self.next_period = "1"

    def _now(self) -> int:
        s = gl.message_raw["datetime"]
        return int(_dt.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp())

    def _payout(self, to_addr: str, amount: int):
        assert gl.wasi.get_self_balance() >= amount, "Contract insolvent"
        _glc.gl_call_generic(
            {'EthSend': {'address': Address(to_addr), 'calldata': b'', 'value': amount}},
            lambda _x: None,
        ).get()

    @gl.public.write.payable
    def create_job(self, worker: str, role: str, rubric: str, rate: int, appeal_window_sec: int):
        # Studio's "value" field = GenLayer payable convention; here it is the locked payroll budget.
        assert rate > 0, "Rate must be positive"
        assert len(rubric) > 0, "Rubric required"
        assert appeal_window_sec >= 60, "Window too short"
        jid = int(self.next_job)
        self.next_job = str(jid + 1)
        self.jobs[str(jid)] = json.dumps({
            "employer": str(gl.message.sender_address),
            "worker": worker,
            "role": role,
            "rubric": rubric,
            "rate": rate,
            "appeal_window_sec": appeal_window_sec,
            "budget": int(gl.message.value),
            "open_period": None,
        })
        return jid

    @gl.public.write.payable
    def top_up(self, job_id: int):
        job = json.loads(self.jobs[str(job_id)])
        assert gl.message.sender_address == Address(job["employer"]), "Only the employer"
        job["budget"] = job["budget"] + int(gl.message.value)
        self.jobs[str(job_id)] = json.dumps(job)

    @gl.public.write
    def submit_period(self, job_id: int, hours: int, items_json: str):
        job = json.loads(self.jobs[str(job_id)])
        assert gl.message.sender_address == Address(job["worker"]), "Only the worker"
        assert job["open_period"] is None, "Previous period still open"
        assert hours > 0, "Hours must be positive"
        items = json.loads(items_json)
        assert isinstance(items, list) and 1 <= len(items) <= MAX_ITEMS, "1 to 3 items"
        for it in items:
            assert len(it.get("url", "")) > 0 and len(it.get("desc", "")) > 0, "Each item needs desc and url"
        need = (hours * job["rate"] * 125 * 10**18) // 100
        assert job["budget"] >= need, "Budget must cover claimed hours at max multiplier"
        pid = int(self.next_period)
        self.next_period = str(pid + 1)
        job["open_period"] = pid
        self.jobs[str(job_id)] = json.dumps(job)
        self.periods[str(pid)] = json.dumps({
            "job_id": job_id,
            "worker": job["worker"],
            "hours": hours,
            "items": items,
            "status": "submitted",
            "tier": None,
            "pay": 0,
            "fetch_failures": 0,
            "appeals_used": 0,
            "adjudicated_at": None,
            "ai_reasoning": None,
        })
        return pid

    def _ai_round(self, job, period) -> str:
        def get_tier() -> str:
            try:
                evidence = _fetch_all(period["items"])
                prompt = (
                    "You are an impartial work-quality auditor for a payroll contract.\n"
                    f"Role: {job['role']}\n"
                    f"Agreed rubric: {job['rubric']}\n"
                    f"Claimed hours this period: {period['hours']}\n\n"
                    f"Evidence:\n{evidence}\n\n"
                    "Evaluate against the rubric: does the evidence verify the claimed items, "
                    "is the work substantial, and does it show real impact? "
                    "Answer with ONE word only: HIGH, MEDIUM, LOW, or UNVERIFIABLE."
                )
                answer = gl.nondet.exec_prompt(prompt).strip().upper()
                for t in ("HIGH", "MEDIUM", "LOW", "UNVERIFIABLE"):
                    if t in answer:
                        return t
                return "UNVERIFIABLE"
            except Exception:
                return "UNREACHABLE"
        return gl.eq_principle.strict_eq(get_tier)

    @gl.public.write
    def resolve_period(self, period_id: int):
        period = json.loads(self.periods[str(period_id)])
        assert period["status"] in ("submitted", "disputed"), "Not resolvable"
        job = json.loads(self.jobs[str(period["job_id"])])
        tier = self._ai_round(job, period)
        if tier == "UNREACHABLE":
            period["fetch_failures"] = period["fetch_failures"] + 1
            if period["fetch_failures"] >= MAX_FETCH_FAILURES:
                period["status"] = "unresolvable"
                period["ai_reasoning"] = "Evidence unreachable after 3 attempts; worker may resubmit or employer dismiss"
            else:
                period["ai_reasoning"] = "Fetch failed (attempt " + str(period["fetch_failures"]) + " of 3); retry allowed"
            self.periods[str(period_id)] = json.dumps(period)
            return
        mult = {"HIGH": 125, "MEDIUM": 100, "LOW": 75, "UNVERIFIABLE": 0}[tier]
        period["tier"] = tier
        period["pay"] = (period["hours"] * job["rate"] * mult * 10**18) // 100
        period["status"] = "adjudicated"
        period["adjudicated_at"] = self._now()
        period["ai_reasoning"] = ("FINAL appeal round: " if period["appeals_used"] > 0 else "") + "AI auditors voted " + tier
        self.periods[str(period_id)] = json.dumps(period)

    @gl.public.write
    def appeal(self, period_id: int):
        period = json.loads(self.periods[str(period_id)])
        assert period["status"] == "adjudicated", "Not adjudicated"
        assert period["appeals_used"] == 0, "Appeal already used"
        job = json.loads(self.jobs[str(period["job_id"])])
        assert self._now() < period["adjudicated_at"] + job["appeal_window_sec"], "Appeal window closed"
        sender = str(gl.message.sender_address)
        assert sender in (job["employer"], period["worker"]), "Not a party"
        period["appeals_used"] = 1
        period["status"] = "disputed"
        period["ai_reasoning"] = "Appeal filed; second audit round will be final"
        self.periods[str(period_id)] = json.dumps(period)

    @gl.public.write
    def finalize(self, period_id: int):
        period = json.loads(self.periods[str(period_id)])
        assert period["status"] == "adjudicated", "Not adjudicated"
        job = json.loads(self.jobs[str(period["job_id"])])
        window_closed = self._now() > period["adjudicated_at"] + job["appeal_window_sec"]
        assert period["appeals_used"] == 1 or window_closed, "Appeal window open: wait or appeal"
        pay = period["pay"]
        assert job["budget"] >= pay, "Job budget insufficient"
        job["budget"] = job["budget"] - pay
        job["open_period"] = None
        self.jobs[str(period["job_id"])] = json.dumps(job)
        period["status"] = "paid"
        self.periods[str(period_id)] = json.dumps(period)
        if pay > 0:
            self._payout(period["worker"], pay)

    @gl.public.write
    def dismiss(self, period_id: int):
        period = json.loads(self.periods[str(period_id)])
        assert period["status"] == "unresolvable", "Not unresolvable"
        job = json.loads(self.jobs[str(period["job_id"])])
        assert gl.message.sender_address == Address(job["employer"]), "Only the employer"
        period["status"] = "dismissed"
        period["ai_reasoning"] = "Dismissed by employer after unreachable evidence"
        job["open_period"] = None
        self.jobs[str(period["job_id"])] = json.dumps(job)
        self.periods[str(period_id)] = json.dumps(period)

    @gl.public.write
    def recover_budget(self, job_id: int):
        job = json.loads(self.jobs[str(job_id)])
        assert gl.message.sender_address == Address(job["employer"]), "Only the employer"
        amount = job["budget"]
        assert amount > 0, "Nothing to recover"
        job["budget"] = 0
        self.jobs[str(job_id)] = json.dumps(job)
        self._payout(job["employer"], amount)

    @gl.public.view
    def get_job(self, job_id: int) -> str:
        return self.jobs.get(str(job_id), "{}")

    @gl.public.view
    def get_period(self, period_id: int) -> str:
        return self.periods.get(str(period_id), "{}")

    @gl.public.view
    def contract_balance(self) -> int:
        return int(gl.wasi.get_self_balance())
