import pytest

from conftest import BOND, GEN, MAX_LIABILITY, WINDOW, iso


def _audited(c, employer, worker, score=80, bond=BOND):
    aid = c.create(employer, worker, bond=bond)
    c.mock_evidence()
    c.mock_audit(True, score)
    c.submit(worker, aid)
    c.audit(aid)
    return aid


def test_appeal_requires_an_audited_tranche(funded, direct_alice, direct_bob):
    c = funded
    aid = c.create(direct_alice, direct_bob)
    c.mock_evidence()
    c.submit(direct_bob, aid)
    with pytest.raises(Exception, match="not in the appeal window"):
        c.appeal(direct_bob, aid)


def test_appeal_only_by_worker(funded, direct_alice, direct_bob):
    c = funded
    aid = _audited(c, direct_alice, direct_bob)
    with pytest.raises(Exception, match="Only the worker may appeal"):
        c.appeal(direct_alice, aid)


def test_appeal_posts_the_bond_into_the_vault(funded, direct_alice, direct_bob):
    c = funded
    aid = _audited(c, direct_alice, direct_bob)
    worker_before = c.balance(direct_bob)
    c.appeal(direct_bob, aid)
    tranche = c.tranche(aid)
    assert tranche["status"] == "appealed"
    assert tranche["appeal_bond_posted"] == str(BOND)
    assert c.balance(direct_bob) == worker_before - BOND
    state = c.vault_state()
    assert state["vault_custody_balance"] == str(MAX_LIABILITY + BOND)
    assert state["active_appeal_bonds"] == str(BOND)
    assert state["locked_payroll_escrows"] == str(MAX_LIABILITY)
    assert c.invariant() is True


def test_appeal_with_zero_bond_is_allowed(funded, direct_alice, direct_bob):
    c = funded
    aid = _audited(c, direct_alice, direct_bob, bond=0)
    worker_before = c.balance(direct_bob)
    c.appeal(direct_bob, aid)
    assert c.tranche(aid)["status"] == "appealed"
    assert c.tranche(aid)["appeal_bond_posted"] == "0"
    assert c.balance(direct_bob) == worker_before
    assert c.vault_state()["active_appeal_bonds"] == "0"
    assert c.invariant() is True


def test_appeal_after_window_closes_reverts(funded, direct_alice, direct_bob):
    c = funded
    aid = _audited(c, direct_alice, direct_bob)
    c.add_time(WINDOW + 1)
    with pytest.raises(Exception, match="Appeal window closed"):
        c.appeal(direct_bob, aid)


def test_appeal_at_the_exact_boundary_reverts(funded, direct_alice, direct_bob):
    c = funded
    aid = _audited(c, direct_alice, direct_bob)
    deadline = c.tranche(aid)["appeal_deadline_clock"]
    c.set_time(iso(deadline))
    with pytest.raises(Exception, match="Appeal window closed"):
        c.appeal(direct_bob, aid)


def test_appeal_one_tick_before_boundary_succeeds(funded, direct_alice, direct_bob):
    c = funded
    aid = _audited(c, direct_alice, direct_bob)
    deadline = c.tranche(aid)["appeal_deadline_clock"]
    c.set_time(iso(deadline - 1))
    c.appeal(direct_bob, aid)
    assert c.tranche(aid)["status"] == "appealed"


def test_appeal_twice_is_rejected(funded, direct_alice, direct_bob):
    c = funded
    aid = _audited(c, direct_alice, direct_bob)
    c.appeal(direct_bob, aid)
    c.mock_audit(True, 80)
    c.resolve_appeal(aid)
    with pytest.raises(Exception, match="Appeal already resolved"):
        c.appeal(direct_bob, aid)


def test_appeal_rejects_insufficient_bond_balance(funded, direct_alice, direct_bob):
    c = funded
    # The worker only holds BOND (2 GEN); a 5 GEN bond cannot be posted.
    aid = _audited(c, direct_alice, direct_bob, bond=5 * GEN)
    with pytest.raises(Exception, match="Insufficient FPT for appeal bond"):
        c.appeal(direct_bob, aid)
    assert c.tranche(aid)["status"] == "audited"
    assert c.invariant() is True


def test_resolve_requires_an_appealed_tranche(funded, direct_alice, direct_bob):
    c = funded
    aid = _audited(c, direct_alice, direct_bob)
    with pytest.raises(Exception, match="not under appeal"):
        c.resolve_appeal(aid)


def test_resolve_with_higher_band_refunds_the_bond(funded, direct_alice, direct_bob):
    c = funded
    aid = _audited(c, direct_alice, direct_bob, score=50)
    c.appeal(direct_bob, aid)
    worker_after_bond = c.balance(direct_bob)
    c.mock_audit(True, 100)
    assert c.resolve_appeal(aid) == 100
    tranche = c.tranche(aid)
    assert tranche["appeal_resolved"] is True
    assert tranche["bond_outcome"] == "refunded"
    assert tranche["worker_payout"] == str(MAX_LIABILITY)
    assert c.balance(direct_bob) == worker_after_bond + BOND
    assert c.vault_state()["active_appeal_bonds"] == "0"
    assert c.invariant() is True


@pytest.mark.parametrize("second", [80, 50, 0])
def test_resolve_without_improvement_forfeits_the_bond(funded, direct_alice, direct_bob, second):
    c = funded
    aid = _audited(c, direct_alice, direct_bob, score=80)
    c.appeal(direct_bob, aid)
    employer_before = c.balance(direct_alice)
    c.mock_audit(True, second)
    c.resolve_appeal(aid)
    tranche = c.tranche(aid)
    assert tranche["bond_outcome"] == "forfeited"
    assert c.balance(direct_alice) == employer_before + BOND
    assert c.vault_state()["active_appeal_bonds"] == "0"
    assert c.invariant() is True


def test_resolve_is_permissionless(funded, direct_alice, direct_bob, direct_charlie):
    c = funded
    aid = _audited(c, direct_alice, direct_bob, score=50)
    c.appeal(direct_bob, aid)
    c.mock_audit(True, 80)
    c.vm.sender = direct_charlie
    assert c.c.resolve_appeal_live(aid, 0) == 80
    assert c.tranche(aid)["appeal_resolved"] is True


def test_resolve_unreachable_reverts_and_keeps_the_bond(funded, direct_alice, direct_bob):
    c = funded
    aid = _audited(c, direct_alice, direct_bob)
    c.appeal(direct_bob, aid)
    c.mock_evidence(body="")
    with pytest.raises(Exception, match="Evidence unreachable at appeal audit time"):
        c.resolve_appeal(aid)
    assert c.tranche(aid)["status"] == "appealed"
    assert c.tranche(aid)["appeal_bond_posted"] == str(BOND)
    assert c.vault_state()["active_appeal_bonds"] == str(BOND)
    assert c.invariant() is True


def test_settlement_after_appeal_uses_the_final_band(funded, direct_alice, direct_bob):
    c = funded
    aid = _audited(c, direct_alice, direct_bob, score=50)
    c.appeal(direct_bob, aid)
    c.mock_audit(True, 80)
    c.resolve_appeal(aid)
    rid = c.settle(aid)
    receipt = c.receipt(rid)
    assert receipt["payroll_band"] == "STANDARD_TARGET_PAYOUT"
    assert receipt["delivery_anchor"] == 80
    assert receipt["worker_payout"] == str(76 * GEN)
    assert receipt["bonds_refunded"] == str(BOND)
    assert c.balance(direct_bob) == BOND + 76 * GEN
    assert c.invariant() is True


def test_appeal_resolution_updates_the_vault_invariant(funded, direct_alice, direct_bob):
    c = funded
    aid = _audited(c, direct_alice, direct_bob, score=80)
    assert c.invariant() is True
    c.appeal(direct_bob, aid)
    assert c.invariant() is True
    c.mock_audit(True, 80)
    c.resolve_appeal(aid)
    assert c.invariant() is True
    assert c.vault_state()["vault_custody_balance"] == str(MAX_LIABILITY)
