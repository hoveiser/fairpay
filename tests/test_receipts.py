from conftest import BOND, GEN, MAX_LIABILITY, WINDOW, addr


def test_audited_settlement_receipt_fields(funded, direct_alice, direct_bob):
    c = funded
    aid = c.create(direct_alice, direct_bob)
    c.mock_evidence()
    c.mock_audit(True, 80)
    c.submit(direct_bob, aid)
    c.audit(aid)
    c.add_time(WINDOW + 1)
    rid = c.settle(aid)
    receipt = c.receipt(rid)
    assert receipt["receipt_id"] == rid
    assert receipt["agreement_id"] == aid
    assert receipt["kind"] == "AUDITED"
    assert receipt["payroll_band"] == "STANDARD_TARGET_PAYOUT"
    assert receipt["delivery_anchor"] == 80
    assert receipt["worker_payout"] == str(76 * GEN)
    assert receipt["employer_refund"] == str(4 * GEN)
    assert receipt["mutual_bps"] == 0
    assert receipt["bonds_refunded"] == "0"
    assert receipt["bonds_forfeited"] == "0"
    assert receipt["settled_at"] == c.now()


def test_receipt_records_the_two_party_addresses(funded, direct_alice, direct_bob):
    c = funded
    aid = c.create(direct_alice, direct_bob)
    c.mock_evidence()
    c.mock_audit(True, 80)
    c.submit(direct_bob, aid)
    c.audit(aid)
    c.add_time(WINDOW + 1)
    rid = c.settle(aid)
    receipt = c.receipt(rid)
    assert receipt["worker"].lower() == addr(direct_bob).lower()
    assert receipt["employer"].lower() == addr(direct_alice).lower()


def test_mutual_receipt_fields(funded, direct_alice, direct_bob):
    c = funded
    aid = c.create(direct_alice, direct_bob)
    c.mutual(direct_alice, aid, 7000)
    rid = c.mutual(direct_bob, aid, 7000)
    receipt = c.receipt(rid)
    assert receipt["kind"] == "MUTUAL"
    assert receipt["payroll_band"] == "MUTUAL_COSIGN"
    assert receipt["delivery_anchor"] == 0
    assert receipt["mutual_bps"] == 7000
    assert receipt["worker_payout"] == str(56 * GEN)
    assert receipt["employer_refund"] == str(24 * GEN)


def test_surplus_recovery_receipt(funded, direct_alice, direct_bob):
    c = funded
    aid = c.create(direct_alice, direct_bob)
    c.mock_evidence()
    c.mock_audit(True, 80)
    c.submit(direct_bob, aid)
    c.audit(aid)
    c.add_time(WINDOW + 1)
    c.recover(direct_alice, aid)
    rid = c.agreement(aid)["receipt_id"]
    receipt = c.receipt(rid)
    assert receipt["kind"] == "SURPLUS_RECOVERY"
    assert receipt["worker_payout"] == "0"
    assert receipt["employer_refund"] == str(4 * GEN)
    assert receipt["payroll_band"] == "SURPLUS_RECOVERY"


def test_receipt_ids_increment(funded, direct_alice, direct_bob):
    c = funded
    c.deposit(direct_alice, 200 * GEN)
    a1 = c.create(direct_alice, direct_bob)
    c.mutual(direct_alice, a1, 5000)
    rid1 = c.mutual(direct_bob, a1, 5000)
    a2 = c.create(direct_alice, direct_bob)
    c.mutual(direct_alice, a2, 5000)
    rid2 = c.mutual(direct_bob, a2, 5000)
    assert rid1 == 1
    assert rid2 == 2
    assert c.receipt(1)["agreement_id"] == a1
    assert c.receipt(2)["agreement_id"] == a2


def test_unknown_receipt_is_empty(funded):
    c = funded
    assert c.c.get_settlement_receipt(999) == "{}"


def test_appeal_bond_refund_is_recorded(funded, direct_alice, direct_bob):
    c = funded
    aid = c.create(direct_alice, direct_bob)
    c.mock_evidence()
    c.mock_audit(True, 50)
    c.submit(direct_bob, aid)
    c.audit(aid)
    c.appeal(direct_bob, aid)
    c.mock_audit(True, 100)
    c.resolve_appeal(aid)
    rid = c.settle(aid)
    receipt = c.receipt(rid)
    assert receipt["bonds_refunded"] == str(BOND)
    assert receipt["bonds_forfeited"] == "0"


def test_appeal_bond_forfeit_is_recorded(funded, direct_alice, direct_bob):
    c = funded
    aid = c.create(direct_alice, direct_bob)
    c.mock_evidence()
    c.mock_audit(True, 80)
    c.submit(direct_bob, aid)
    c.audit(aid)
    c.appeal(direct_bob, aid)
    c.mock_audit(True, 80)
    c.resolve_appeal(aid)
    rid = c.settle(aid)
    receipt = c.receipt(rid)
    assert receipt["bonds_refunded"] == "0"
    assert receipt["bonds_forfeited"] == str(BOND)


def test_multi_tranche_receipt_summarizes(funded, direct_alice, direct_bob):
    c = funded
    aid = c.create(direct_alice, direct_bob, tranches=2)
    c.mock_evidence()
    c.mock_audit(True, 100)
    c.submit(direct_bob, aid, idx=0)
    c.audit(aid, 0)
    # A tranche stays active through its appeal window, so the next tranche can
    # only start after the window closes with no appeal.
    c.add_time(WINDOW + 1)
    c.submit(direct_bob, aid, idx=1)
    c.audit(aid, 1)
    c.add_time(WINDOW + 1)
    rid = c.settle(aid)
    receipt = c.receipt(rid)
    assert receipt["payroll_band"] == "MULTI_TRANCHE"
    assert receipt["delivery_anchor"] == 0
    assert receipt["worker_payout"] == str(MAX_LIABILITY)
    assert receipt["employer_refund"] == "0"
