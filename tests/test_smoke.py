from conftest import BOND, GEN, MAX_LIABILITY


def test_smoke_audit_and_settle(funded, direct_alice, direct_bob):
    c = funded
    assert c.balance(direct_alice) == 200 * GEN - BOND
    aid = c.create(direct_alice, direct_bob)
    assert c.agreement(aid)["max_liability"] == str(MAX_LIABILITY)
    assert c.vault_state()["vault_custody_balance"] == str(MAX_LIABILITY)
    c.mock_evidence()
    c.mock_audit(True, 80)
    c.submit(direct_bob, aid)
    anchor = c.audit(aid)
    assert anchor == 80
    assert c.tranche(aid)["payroll_band"] == "STANDARD_TARGET_PAYOUT"
    assert c.tranche(aid)["worker_payout"] == str(60 * GEN + 16 * GEN)
    assert c.run_validator() is True
    c.add_time(121)
    rid = c.settle(aid)
    assert c.balance(direct_bob) == 76 * GEN + BOND
    assert c.agreement(aid)["status"] == "SETTLED"
    assert c.receipt(rid)["worker_payout"] == str(76 * GEN)
    assert c.invariant() is True
