import pytest

from conftest import BOND, GEN, MAX_LIABILITY


def _create(c, employer, worker):
    c.mock_evidence()
    return c.create(employer, worker)


def test_single_employer_call_only_records(funded, direct_alice, direct_bob):
    c = funded
    aid = _create(c, direct_alice, direct_bob)
    vault_before = c.vault_state()["vault_custody_balance"]
    employer_before = c.balance(direct_alice)
    assert c.mutual(direct_alice, aid, 7000) == 0
    agreement = c.agreement(aid)
    assert agreement["status"] == "OPEN"
    assert agreement["mutual"]["employer_signed"] is True
    assert agreement["mutual"]["worker_signed"] is False
    assert agreement["locked_amount"] == str(MAX_LIABILITY)
    assert c.vault_state()["vault_custody_balance"] == vault_before
    assert c.balance(direct_alice) == employer_before
    assert c.invariant() is True


def test_single_worker_call_only_records(funded, direct_alice, direct_bob):
    c = funded
    aid = _create(c, direct_alice, direct_bob)
    worker_before = c.balance(direct_bob)
    assert c.mutual(direct_bob, aid, 7000) == 0
    agreement = c.agreement(aid)
    assert agreement["mutual"]["worker_signed"] is True
    assert agreement["mutual"]["employer_signed"] is False
    assert c.balance(direct_bob) == worker_before
    assert c.vault_state()["vault_custody_balance"] == str(MAX_LIABILITY)
    assert c.invariant() is True


def test_matching_signatures_settle_at_shared_bps(funded, direct_alice, direct_bob):
    c = funded
    aid = _create(c, direct_alice, direct_bob)
    c.mutual(direct_alice, aid, 7000)
    rid = c.mutual(direct_bob, aid, 7000)
    agreement = c.agreement(aid)
    receipt = c.receipt(rid)
    assert agreement["status"] == "SETTLED"
    assert agreement["locked_amount"] == "0"
    assert c.balance(direct_bob) == BOND + 56 * GEN
    assert c.balance(direct_alice) == 198 * GEN - MAX_LIABILITY + 24 * GEN
    assert c.vault_state()["vault_custody_balance"] == "0"
    assert receipt["kind"] == "MUTUAL"
    assert receipt["mutual_bps"] == 7000
    assert receipt["worker_payout"] == str(56 * GEN)
    assert receipt["employer_refund"] == str(24 * GEN)
    assert int(receipt["worker_payout"]) + int(receipt["employer_refund"]) == MAX_LIABILITY
    assert c.invariant() is True


def test_zero_bps_gives_everything_to_the_employer(funded, direct_alice, direct_bob):
    c = funded
    aid = _create(c, direct_alice, direct_bob)
    c.mutual(direct_alice, aid, 0)
    c.mutual(direct_bob, aid, 0)
    assert c.balance(direct_bob) == BOND
    assert c.balance(direct_alice) == 198 * GEN
    assert c.vault_state()["vault_custody_balance"] == "0"
    assert c.invariant() is True


def test_full_bps_gives_everything_to_the_worker(funded, direct_alice, direct_bob):
    c = funded
    aid = _create(c, direct_alice, direct_bob)
    c.mutual(direct_alice, aid, 10000)
    c.mutual(direct_bob, aid, 10000)
    assert c.balance(direct_bob) == BOND + MAX_LIABILITY
    assert c.balance(direct_alice) == 198 * GEN - MAX_LIABILITY
    assert c.vault_state()["vault_custody_balance"] == "0"
    assert c.invariant() is True


def test_mismatch_blocks_settlement(funded, direct_alice, direct_bob):
    c = funded
    aid = _create(c, direct_alice, direct_bob)
    c.mutual(direct_alice, aid, 6000)
    with pytest.raises(Exception, match="Co-sign bps mismatch"):
        c.mutual(direct_bob, aid, 7000)
    agreement = c.agreement(aid)
    assert agreement["status"] == "OPEN"
    assert agreement["mutual"]["worker_signed"] is False
    assert c.vault_state()["vault_custody_balance"] == str(MAX_LIABILITY)
    # The worker can still match the standing employer proposal.
    c.mutual(direct_bob, aid, 6000)
    assert c.agreement(aid)["status"] == "SETTLED"


def test_reverse_mismatch_blocks_settlement(funded, direct_alice, direct_bob):
    c = funded
    aid = _create(c, direct_alice, direct_bob)
    c.mutual(direct_bob, aid, 6000)
    with pytest.raises(Exception, match="Co-sign bps mismatch"):
        c.mutual(direct_alice, aid, 7000)
    agreement = c.agreement(aid)
    assert agreement["status"] == "OPEN"
    assert agreement["mutual"]["employer_signed"] is False
    assert agreement["mutual"]["worker_signed"] is True
    assert c.vault_state()["vault_custody_balance"] == str(MAX_LIABILITY)
    # The employer can match the standing worker proposal.
    c.mutual(direct_alice, aid, 6000)
    assert c.agreement(aid)["status"] == "SETTLED"


def test_same_party_can_update_its_own_bps(funded, direct_alice, direct_bob):
    c = funded
    aid = _create(c, direct_alice, direct_bob)
    c.mutual(direct_alice, aid, 7000)
    c.mutual(direct_alice, aid, 8000)
    agreement = c.agreement(aid)
    assert agreement["mutual"]["employer_bps"] == 8000
    assert agreement["status"] == "OPEN"
    c.mutual(direct_bob, aid, 8000)
    assert c.agreement(aid)["status"] == "SETTLED"
    assert c.receipt(1)["worker_payout"] == str(64 * GEN)


def test_non_party_cannot_co_sign(funded, direct_alice, direct_bob, direct_charlie):
    c = funded
    aid = _create(c, direct_alice, direct_bob)
    with pytest.raises(Exception, match="Only a party"):
        c.mutual(direct_charlie, aid, 5000)


@pytest.mark.parametrize("bps", [-1, 10001])
def test_bps_out_of_range(funded, direct_alice, direct_bob, bps):
    c = funded
    aid = _create(c, direct_alice, direct_bob)
    with pytest.raises(Exception, match="Payout bps out of range"):
        c.mutual(direct_alice, aid, bps)


def test_proposal_after_settlement_is_rejected(funded, direct_alice, direct_bob):
    c = funded
    aid = _create(c, direct_alice, direct_bob)
    c.mutual(direct_alice, aid, 5000)
    c.mutual(direct_bob, aid, 5000)
    with pytest.raises(Exception, match="Agreement already settled"):
        c.mutual(direct_alice, aid, 5000)


def test_mutual_settles_an_audited_agreement_before_the_window_ends(funded, direct_alice, direct_bob):
    c = funded
    aid = c.create(direct_alice, direct_bob)
    c.mock_evidence()
    c.mock_audit(True, 80)
    c.submit(direct_bob, aid)
    c.audit(aid)
    assert c.agreement(aid)["status"] == "AUDITED"
    c.mutual(direct_alice, aid, 9000)
    c.mutual(direct_bob, aid, 9000)
    assert c.agreement(aid)["status"] == "SETTLED"
    assert c.balance(direct_bob) == BOND + 72 * GEN
    assert c.invariant() is True


def test_mutual_settles_a_submitted_agreement(funded, direct_alice, direct_bob):
    c = funded
    aid = c.create(direct_alice, direct_bob)
    c.mock_evidence()
    c.submit(direct_bob, aid)
    c.mutual(direct_alice, aid, 2500)
    c.mutual(direct_bob, aid, 2500)
    agreement = c.agreement(aid)
    assert agreement["status"] == "SETTLED"
    assert c.tranche(aid)["status"] == "settled_mutual"
    assert c.balance(direct_bob) == BOND + 20 * GEN
    assert c.invariant() is True


def test_mutual_blocked_after_partial_surplus_recovery(funded, direct_alice, direct_bob):
    c = funded
    aid = c.create(direct_alice, direct_bob)
    c.mock_evidence()
    c.mock_audit(True, 80)
    c.submit(direct_bob, aid)
    c.audit(aid)
    c.add_time(121)
    c.recover(direct_alice, aid)
    with pytest.raises(Exception, match="partially settled"):
        c.mutual(direct_alice, aid, 5000)


def test_mutual_parties_can_be_the_same_order_reversed(funded, direct_alice, direct_bob):
    c = funded
    aid = _create(c, direct_alice, direct_bob)
    c.mutual(direct_bob, aid, 4000)
    c.mutual(direct_alice, aid, 4000)
    receipt = c.receipt(c.agreement(aid)["receipt_id"])
    assert receipt["worker_payout"] == str(32 * GEN)
    assert receipt["employer_refund"] == str(48 * GEN)
    assert c.invariant() is True
