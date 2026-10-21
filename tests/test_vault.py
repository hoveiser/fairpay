import pytest

from conftest import GEN, addr


def test_deposit_mints_one_to_one(fp, direct_alice):
    c = fp()
    c.deposit(direct_alice, 50 * GEN)
    assert c.balance(direct_alice) == 50 * GEN
    state = c.vault_state()
    assert state["total_fpt_supply"] == str(50 * GEN)
    assert state["vault_custody_balance"] == "0"
    assert state["native_backed"] is True
    assert c.invariant() is True


def test_deposit_rejects_zero_value(fp, direct_alice):
    c = fp()
    c.vm.sender = direct_alice
    c.vm.value = 0
    with pytest.raises(Exception, match="Deposit must be positive"):
        c.c.faucet_or_deposit()


def test_deposits_from_two_accounts_accumulate(fp, direct_alice, direct_bob):
    c = fp()
    c.deposit(direct_alice, 30 * GEN)
    c.deposit(direct_bob, 20 * GEN)
    assert c.balance(direct_alice) == 30 * GEN
    assert c.balance(direct_bob) == 20 * GEN
    assert c.vault_state()["total_fpt_supply"] == str(50 * GEN)
    assert c.invariant() is True


def test_transfer_moves_fpt(fp, direct_alice, direct_bob):
    c = fp()
    c.deposit(direct_alice, 10 * GEN)
    c.transfer(direct_alice, direct_bob, 4 * GEN)
    assert c.balance(direct_alice) == 6 * GEN
    assert c.balance(direct_bob) == 4 * GEN
    assert c.vault_state()["total_fpt_supply"] == str(10 * GEN)
    assert c.invariant() is True


def test_transfer_rejects_zero_recipient(fp, direct_alice):
    c = fp()
    c.deposit(direct_alice, 10 * GEN)
    with pytest.raises(Exception, match="Recipient must not be zero"):
        c.transfer(direct_alice, "0x" + "0" * 40, GEN)


def test_transfer_rejects_self(fp, direct_alice):
    c = fp()
    c.deposit(direct_alice, 10 * GEN)
    with pytest.raises(Exception, match="Recipient must differ from sender"):
        c.transfer(direct_alice, direct_alice, GEN)


def test_transfer_rejects_insufficient_balance(fp, direct_alice, direct_bob):
    c = fp()
    c.deposit(direct_alice, 10 * GEN)
    with pytest.raises(Exception, match="Insufficient FPT balance"):
        c.transfer(direct_alice, direct_bob, 11 * GEN)


@pytest.mark.parametrize("bad", ["0x123", "not-an-address", "0x" + "g" * 40])
def test_transfer_rejects_invalid_address(fp, direct_alice, bad):
    c = fp()
    c.deposit(direct_alice, 10 * GEN)
    with pytest.raises(Exception, match="Invalid recipient address"):
        c.transfer(direct_alice, bad, GEN)


def test_transfer_rejects_zero_amount(fp, direct_alice, direct_bob):
    c = fp()
    c.deposit(direct_alice, 10 * GEN)
    with pytest.raises(Exception, match="Amount must be positive"):
        c.transfer(direct_alice, direct_bob, 0)


def test_transfer_rejects_negative_amount(fp, direct_alice, direct_bob):
    c = fp()
    c.deposit(direct_alice, 10 * GEN)
    with pytest.raises(Exception, match="Amount must be positive"):
        c.transfer(direct_alice, direct_bob, -1)


def test_unknown_balance_is_zero(fp, direct_charlie):
    c = fp()
    assert c.balance(direct_charlie) == 0


def test_native_backing_covers_supply(fp, direct_alice):
    c = fp(native_balance=100 * GEN)
    c.deposit(direct_alice, 50 * GEN)
    state = c.vault_state()
    assert int(state["native_backing"]) >= int(state["total_fpt_supply"])
    assert state["native_backed"] is True


def test_vault_state_empty(fp):
    c = fp()
    state = c.vault_state()
    assert state["vault_custody_balance"] == "0"
    assert state["locked_payroll_escrows"] == "0"
    assert state["active_appeal_bonds"] == "0"
    assert state["agreement_count"] == 0
    assert c.invariant() is True


def test_transfer_does_not_change_vault_or_supply(fp, direct_alice, direct_bob):
    c = fp()
    c.deposit(direct_alice, 40 * GEN)
    before = c.vault_state()
    c.transfer(direct_alice, direct_bob, 15 * GEN)
    after = c.vault_state()
    assert before["total_fpt_supply"] == after["total_fpt_supply"]
    assert after["vault_custody_balance"] == "0"
    assert c.invariant() is True
