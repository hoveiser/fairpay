import pytest

from conftest import BOND, GEN, MAX_LIABILITY


def _audited(c, employer, worker, score=80):
    aid = c.create(employer, worker)
    c.mock_evidence()
    c.mock_audit(True, score)
    c.submit(worker, aid)
    c.audit(aid)
    return aid


def _under_appeal(c, employer, worker, first=80, second=80):
    aid = _audited(c, employer, worker, first)
    c.appeal(worker, aid)
    c.mock_audit(True, second)
    c.resolve_appeal(aid)
    return aid


def test_recover_blocked_while_submitted(funded, direct_alice, direct_bob):
    c = funded
    aid = c.create(direct_alice, direct_bob)
    c.mock_evidence()
    c.submit(direct_bob, aid)
    with pytest.raises(Exception, match="All tranches must be final"):
        c.recover(direct_alice, aid)
    assert c.invariant() is True


def test_recover_blocked_while_appeal_window_open(funded, direct_alice, direct_bob):
    c = funded
    aid = _audited(c, direct_alice, direct_bob, 80)
    with pytest.raises(Exception, match="Appeal window open: liability locked"):
        c.recover(direct_alice, aid)
    assert c.reserved(aid) == MAX_LIABILITY
    assert c.invariant() is True


def test_recover_blocked_while_appeal_pending(funded, direct_alice, direct_bob):
    c = funded
    aid = _audited(c, direct_alice, direct_bob, 80)
    c.appeal(direct_bob, aid)
    with pytest.raises(Exception, match="Appeal pending: liability locked"):
        c.recover(direct_alice, aid)
    assert c.vault_state()["active_appeal_bonds"] == str(BOND)
    assert c.invariant() is True


def test_recover_accepted_after_window_closes_with_exact_surplus(funded, direct_alice, direct_bob):
    c = funded
    aid = _audited(c, direct_alice, direct_bob, 80)
    employer_before = c.balance(direct_alice)
    c.add_time(121)
    recovered = c.recover(direct_alice, aid)
    assert recovered == 4 * GEN
    assert c.balance(direct_alice) == employer_before + 4 * GEN
    assert c.agreement(aid)["locked_amount"] == str(76 * GEN)
    assert c.vault_state()["vault_custody_balance"] == str(76 * GEN)
    assert c.reserved(aid) == 76 * GEN
    assert c.invariant() is True


def test_recover_rejects_when_full_payout_is_owed(funded, direct_alice, direct_bob):
    c = funded
    aid = _audited(c, direct_alice, direct_bob, 100)
    c.add_time(121)
    with pytest.raises(Exception, match="No unearned surplus"):
        c.recover(direct_alice, aid)
    assert c.invariant() is True


def test_recover_after_appeal_without_improvement(funded, direct_alice, direct_bob):
    c = funded
    aid = _under_appeal(c, direct_alice, direct_bob, first=80, second=80)
    # Equal payout means the bond was forfeited to the employer.
    assert c.tranche(aid)["bond_outcome"] == "forfeited"
    recovered = c.recover(direct_alice, aid)
    assert recovered == 4 * GEN
    assert c.invariant() is True


def test_recover_after_appeal_with_improvement(funded, direct_alice, direct_bob):
    c = funded
    aid = _under_appeal(c, direct_alice, direct_bob, first=50, second=80)
    assert c.tranche(aid)["bond_outcome"] == "refunded"
    assert c.reserved(aid) == MAX_LIABILITY
    recovered = c.recover(direct_alice, aid)
    assert recovered == 4 * GEN
    assert c.agreement(aid)["locked_amount"] == str(76 * GEN)
    assert c.invariant() is True


def test_recover_twice_is_rejected(funded, direct_alice, direct_bob):
    c = funded
    aid = _audited(c, direct_alice, direct_bob, 80)
    c.add_time(121)
    c.recover(direct_alice, aid)
    with pytest.raises(Exception, match="Surplus already recovered"):
        c.recover(direct_alice, aid)


def test_recover_only_employer(funded, direct_alice, direct_bob):
    c = funded
    aid = _audited(c, direct_alice, direct_bob, 80)
    c.add_time(121)
    with pytest.raises(Exception, match="Only the employer"):
        c.recover(direct_bob, aid)


def test_recover_after_settlement_is_rejected(funded, direct_alice, direct_bob):
    c = funded
    aid = _audited(c, direct_alice, direct_bob, 80)
    c.add_time(121)
    c.settle(aid)
    with pytest.raises(Exception, match="Agreement already settled"):
        c.recover(direct_alice, aid)


def test_recover_before_any_tranche_is_blocked(funded, direct_alice, direct_bob):
    c = funded
    aid = c.create(direct_alice, direct_bob)
    with pytest.raises(Exception, match="All tranches must be final"):
        c.recover(direct_alice, aid)


def test_recovery_then_settlement_pays_only_the_worker(funded, direct_alice, direct_bob):
    c = funded
    aid = _audited(c, direct_alice, direct_bob, 80)
    c.add_time(121)
    c.recover(direct_alice, aid)
    employer_before = c.balance(direct_alice)
    c.settle(aid)
    assert c.balance(direct_bob) == 76 * GEN + BOND
    assert c.balance(direct_alice) == employer_before
    assert c.vault_state()["vault_custody_balance"] == "0"
    assert c.invariant() is True


def test_reserved_liability_tracks_the_lock(funded, direct_alice, direct_bob):
    c = funded
    aid = c.create(direct_alice, direct_bob)
    assert c.reserved(aid) == MAX_LIABILITY
    c.mock_evidence()
    c.submit(direct_bob, aid)
    assert c.reserved(aid) == MAX_LIABILITY
    c.mock_audit(True, 50)
    c.audit(aid)
    assert c.reserved(aid) == MAX_LIABILITY
    c.add_time(121)
    # The lock stays at the full liability until the employer actually recovers
    # the surplus; the view reports the custody lock, not a hypothetical payout.
    assert c.reserved(aid) == MAX_LIABILITY
    c.recover(direct_alice, aid)
    assert c.reserved(aid) == 70 * GEN
    c.settle(aid)
    assert c.reserved(aid) == 0
