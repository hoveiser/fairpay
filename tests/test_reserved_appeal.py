# PART A — reserved-liability must cover every payout that is still reachable.
# These are the appeal/recovery regression tests the steward found missing.
import pytest

from conftest import GEN, addr, iso, DEFAULT_STALE_WINDOW

T0 = "2026-08-30T12:00:00Z"
WINDOW = 120


def _mk(fp, direct_vm, direct_alice, direct_bob, budget=10 * GEN):
    direct_vm.warp(T0)
    c = fp(budget=budget)
    c.set_time(T0)
    jid = c.create_job(direct_alice, addr(direct_bob), budget=budget,
                       appeal_window=WINDOW, stale_window=DEFAULT_STALE_WINDOW)
    c.mock_evidence("proof of work version 1 - deployed feature with tests and docs, real impact")
    pid = c.submit(direct_bob, jid, 4)
    return c, jid, pid


def _adjudicate(c, pid, tier):
    c.mock_tier(tier)
    c.resolve(pid)


def _assert_reserve_matches_oracle(c, jid):
    # the contract's own view must equal the independent oracle
    assert c.reserved(jid) == c.expected_reserve(jid)


# ---- the steward's exact scenario, for each non-final first ruling ----------
@pytest.mark.parametrize("first_tier", ["LOW", "MEDIUM", "UNVERIFIABLE"])
def test_steward_recover_during_appeal_window_then_high_appeal(direct_vm, fp, direct_alice, direct_bob, first_tier):
    c, jid, pid = _mk(fp, direct_vm, direct_alice, direct_bob)
    _adjudicate(c, pid, first_tier)

    # While the appeal window is open the reserve is the MAX reachable (5 GEN),
    # so recovery may only withdraw the excess above 5, never down to the LOW pay.
    _assert_reserve_matches_oracle(c, jid)
    assert c.reserved(jid) == 5 * GEN
    c.recover(direct_alice, jid)
    assert c.balance(jid) == 5 * GEN
    c.assert_invariant(jid)

    # worker appeals and the second ruling is HIGH -> finalize must be funded
    c.appeal(pid, direct_bob)
    c.mock_tier("HIGH")
    c.resolve(pid)
    assert c.period(pid)["pay"] == 5 * GEN
    c.add_time(WINDOW + 1)
    c.finalize(pid, direct_alice)
    assert c.period(pid)["status"] == "paid"
    assert c.balance(jid) == 0
    # sends[0] was the employer recovery (5 GEN); the finalize payout to the
    # worker is the last EthSend and must be the full 5 GEN HIGH liability.
    assert c.sends[-1]["value"] == 5 * GEN
    assert addr(c.sends[-1]["address"]).lower() == addr(direct_bob).lower()
    c.assert_invariant(jid)


def test_appeal_window_elapsed_releases_to_exact_pay(direct_vm, fp, direct_alice, direct_bob):
    c, jid, pid = _mk(fp, direct_vm, direct_alice, direct_bob)
    _adjudicate(c, pid, "LOW")
    c.add_time(WINDOW + 1)  # window elapsed with no appeal -> truly final
    assert c.reserved(jid) == 3 * GEN  # drops to exact pay
    c.recover(direct_alice, jid)       # now allowed to withdraw down to the pay
    assert c.balance(jid) == 3 * GEN
    c.finalize(pid, direct_alice)
    assert c.period(pid)["status"] == "paid"
    assert c.sends[-1]["value"] == 3 * GEN  # last send is the worker payout
    c.assert_invariant(jid)


def test_appeal_used_and_final_ruling_reserves_exact_pay(direct_vm, fp, direct_alice, direct_bob):
    c, jid, pid = _mk(fp, direct_vm, direct_alice, direct_bob)
    _adjudicate(c, pid, "LOW")
    c.appeal(pid, direct_bob)
    c.mock_tier("MEDIUM")
    c.resolve(pid)  # final appeal round, appeals_used == 1
    assert c.period(pid)["pay"] == 4 * GEN
    assert c.reserved(jid) == 4 * GEN  # truly final: reserve is the exact pay
    c.recover(direct_alice, jid)
    assert c.balance(jid) == 4 * GEN
    c.finalize(pid, direct_alice)
    assert c.period(pid)["status"] == "paid"
    c.assert_invariant(jid)


def test_multiple_periods_mixed_states_sum_is_protected(direct_vm, fp, direct_alice, direct_bob):
    budget = 30 * GEN
    direct_vm.warp(T0)
    c = fp(budget=budget)
    c.set_time(T0)
    jid = c.create_job(direct_alice, addr(direct_bob), budget=budget,
                       appeal_window=WINDOW, stale_window=DEFAULT_STALE_WINDOW)
    c.mock_evidence("proof of work version 1 - deployed feature with tests and docs, real impact")

    # period 1 -> dismissed as stale (releases reservation)
    p1 = c.submit(direct_bob, jid, 4)
    c.add_time(DEFAULT_STALE_WINDOW + 1)
    c.dismiss_stale(direct_alice, p1)

    # period 2 -> paid HIGH (settled, no longer reserves)
    c.set_time(T0)
    p2 = c.submit(direct_bob, jid, 4)
    c.mock_tier("HIGH")
    c.resolve(p2)
    c.add_time(WINDOW + 1)
    c.finalize(p2, direct_alice)

    # period 3 -> adjudicated LOW with the appeal window still open (reserves MAX)
    c.set_time(T0)
    p3 = c.submit(direct_bob, jid, 4)
    _adjudicate(c, p3, "LOW")

    # only period 3 (the live one) is reserved; sum across all periods == 5 GEN
    _assert_reserve_matches_oracle(c, jid)
    assert c.reserved(jid) == 5 * GEN

    c.recover(direct_alice, jid)  # withdraw budget - 5*GEN; protects the live appeal
    assert c.balance(jid) == 5 * GEN
    c.assert_invariant(jid)

    # period 2 stays intact (already paid), period 3 appeals to HIGH and finalizes
    assert c.period(p2)["status"] == "paid"
    c.appeal(p3, direct_bob)
    c.mock_tier("HIGH")
    c.resolve(p3)
    c.add_time(WINDOW + 1)
    c.finalize(p3, direct_alice)
    assert c.period(p3)["status"] == "paid"
    assert c.balance(jid) == 0
    c.assert_invariant(jid)


def test_appeal_boundary_single_shared_predicate(direct_vm, fp, direct_alice, direct_bob):
    # Pin the exact-boundary behavior: recover/reserve sees "window closed" on the
    # SAME tick that appeal() rejects, with no one-second gap.
    c, jid, pid = _mk(fp, direct_vm, direct_alice, direct_bob)
    _adjudicate(c, pid, "LOW")
    adjudicated_at = c.period(pid)["adjudicated_at"]

    # one tick BEFORE the boundary: window open -> reserve is MAX; appeal works;
    # finalize must be blocked.
    c.set_time(iso(adjudicated_at + WINDOW - 1))
    _assert_reserve_matches_oracle(c, jid)
    assert c.reserved(jid) == 5 * GEN
    with pytest.raises(AssertionError, match="Appeal window open"):
        c.finalize(pid, direct_alice)
    c.assert_invariant(jid)

    # AT the boundary: window closed -> reserve drops to exact pay; appeal is
    # rejected; finalize is allowed. Consistent on the same tick.
    c.set_time(iso(adjudicated_at + WINDOW))
    _assert_reserve_matches_oracle(c, jid)
    assert c.reserved(jid) == 3 * GEN
    with pytest.raises(AssertionError, match="Appeal window closed"):
        c.appeal(pid, direct_bob)
    c.recover(direct_alice, jid)  # may now withdraw down to the exact pay
    assert c.balance(jid) == 3 * GEN
    c.finalize(pid, direct_alice)
    assert c.period(pid)["status"] == "paid"
    c.assert_invariant(jid)
