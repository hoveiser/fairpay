from conftest import GEN, MAX_LIABILITY


def _oracle(c, last_id):
    locked = 0
    bonds = 0
    for aid in range(1, last_id + 1):
        agreement = c.agreement(aid)
        if agreement["status"] != "SETTLED":
            locked += int(agreement["locked_amount"])
        for idx in agreement.get("tranche_indexes", []):
            tranche = c.tranche(aid, int(idx))
            if tranche["status"] == "appealed":
                bonds += int(tranche["appeal_bond_posted"])
    return locked, bonds


def _assert_invariant(c, last_id):
    locked, bonds = _oracle(c, last_id)
    state = c.vault_state()
    assert state["locked_payroll_escrows"] == str(locked)
    assert state["active_appeal_bonds"] == str(bonds)
    assert state["vault_custody_balance"] == str(locked + bonds)
    assert state["invariant_holds"] is True
    assert c.invariant() is True


def test_single_agreement_invariant_through_every_state(funded, direct_alice, direct_bob):
    c = funded
    aid = c.create(direct_alice, direct_bob)
    _assert_invariant(c, 1)
    c.mock_evidence()
    c.submit(direct_bob, aid)
    _assert_invariant(c, 1)
    c.mock_audit(True, 80)
    c.audit(aid)
    _assert_invariant(c, 1)
    c.appeal(direct_bob, aid)
    _assert_invariant(c, 1)
    c.mock_audit(True, 80)
    c.resolve_appeal(aid)
    _assert_invariant(c, 1)
    c.add_time(121)
    c.recover(direct_alice, aid)
    _assert_invariant(c, 1)
    c.settle(aid)
    _assert_invariant(c, 1)
    assert c.vault_state()["vault_custody_balance"] == "0"


def test_multi_agreement_mixed_states(funded, direct_alice, direct_bob):
    c = funded
    c.deposit(direct_alice, 200 * GEN)
    c.mock_evidence()

    # 1: submitted, full liability locked.
    a1 = c.create(direct_alice, direct_bob)
    c.submit(direct_bob, a1)

    # 2: audited, appeal window still open.
    a2 = c.create(direct_alice, direct_bob, base=20 * GEN, bonus=5 * GEN)
    c.mock_audit(True, 80)
    c.submit(direct_bob, a2)
    c.audit(a2)

    # 3: under appeal, full liability plus the bond are held.
    a3 = c.create(direct_alice, direct_bob, base=20 * GEN, bonus=10 * GEN)
    c.mock_audit(True, 50)
    c.submit(direct_bob, a3)
    c.audit(a3)
    c.appeal(direct_bob, a3)

    # 4: settled by mutual co-sign, nothing remains locked.
    a4 = c.create(direct_alice, direct_bob)
    c.mutual(direct_alice, a4, 10000)
    c.mutual(direct_bob, a4, 10000)

    _assert_invariant(c, 4)
    assert c.vault_state()["vault_custody_balance"] == str(MAX_LIABILITY + 25 * GEN + 30 * GEN + 2 * GEN)

    # Resolve the appeal: improvement refunds the bond, the lock remains.
    c.mock_audit(True, 80)
    c.resolve_appeal(a3)
    _assert_invariant(c, 4)

    # Settle the audited agreement 2 after its window closes.
    c.add_time(121)
    c.recover(direct_alice, a2)
    _assert_invariant(c, 4)
    c.settle(a2)
    _assert_invariant(c, 4)

    # Settle agreement 3, leaving only agreement 1 locked.
    c.settle(a3)
    _assert_invariant(c, 4)
    assert c.vault_state()["vault_custody_balance"] == str(MAX_LIABILITY)

    # Finish agreement 1.
    c.mock_audit(True, 100)
    c.audit(a1)
    c.add_time(121)
    c.settle(a1)
    _assert_invariant(c, 4)
    assert c.vault_state()["vault_custody_balance"] == "0"


def test_multi_tranche_invariant(funded, direct_alice, direct_bob):
    c = funded
    aid = c.create(direct_alice, direct_bob, tranches=2)
    c.mock_evidence()
    c.mock_audit(True, 100)
    c.submit(direct_bob, aid, idx=0)
    c.audit(aid, 0)
    _assert_invariant(c, 1)
    # The second tranche is not submitted yet, so the agreement cannot settle.
    c.add_time(121)
    try:
        c.settle(aid)
        raise AssertionError("settlement should require every tranche")
    except Exception as exc:
        assert "All tranches must be final" in str(exc)
    _assert_invariant(c, 1)
    # Submit and audit the second tranche, then settle both.
    c.submit(direct_bob, aid, idx=1)
    c.audit(aid, 1)
    c.add_time(121)
    c.settle(aid)
    _assert_invariant(c, 1)
    assert c.balance(direct_bob) == 2 * GEN + MAX_LIABILITY
    assert c.vault_state()["vault_custody_balance"] == "0"


def test_native_backing_never_drops_below_supply(funded, direct_alice, direct_bob):
    c = funded
    aid = c.create(direct_alice, direct_bob)
    c.mock_evidence()
    c.mock_audit(True, 80)
    c.submit(direct_bob, aid)
    c.audit(aid)
    c.add_time(121)
    c.settle(aid)
    state = c.vault_state()
    assert int(state["native_backing"]) >= int(state["total_fpt_supply"])
    assert state["native_backed"] is True
    assert state["vault_custody_balance"] == "0"


def test_invariant_holds_after_mutual_settlement(funded, direct_alice, direct_bob):
    c = funded
    aid = c.create(direct_alice, direct_bob)
    c.mutual(direct_alice, aid, 3333)
    _assert_invariant(c, 1)
    c.mutual(direct_bob, aid, 3333)
    _assert_invariant(c, 1)
    assert c.vault_state()["vault_custody_balance"] == "0"
