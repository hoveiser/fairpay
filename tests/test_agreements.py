import json

import pytest

from conftest import (
    BASE,
    BOND,
    BONUS,
    GEN,
    GOOD_URL,
    MAX_LIABILITY,
    WINDOW,
    addr,
)


def test_create_locks_full_max_liability(funded, direct_alice, direct_bob):
    c = funded
    employer_before = c.balance(direct_alice)
    aid = c.create(direct_alice, direct_bob)
    agreement = c.agreement(aid)
    assert agreement["max_liability"] == str(MAX_LIABILITY)
    assert agreement["locked_amount"] == str(MAX_LIABILITY)
    assert c.balance(direct_alice) == employer_before - MAX_LIABILITY
    assert c.vault_state()["vault_custody_balance"] == str(MAX_LIABILITY)
    assert c.reserved(aid) == MAX_LIABILITY
    assert c.invariant() is True


def test_create_rejects_insufficient_balance(fp, direct_alice, direct_bob):
    c = fp()
    with pytest.raises(Exception, match="Insufficient FPT balance"):
        c.create(direct_alice, direct_bob)


@pytest.mark.parametrize(
    "worker",
    [
        "0x" + "0" * 40,
        "0x123",
        "not-an-address",
    ],
)
def test_create_rejects_bad_worker_address(funded, direct_alice, worker):
    c = funded
    with pytest.raises(Exception, match="Worker"):
        c.vm.sender = direct_alice
        c.c.create_payroll_agreement(worker, "dev", "rubric", BASE, BONUS, WINDOW, BOND, 1)


def test_create_rejects_worker_equals_employer(funded, direct_alice):
    c = funded
    with pytest.raises(Exception, match="Worker must differ from employer"):
        c.vm.sender = direct_alice
        c.c.create_payroll_agreement(addr(direct_alice), "dev", "rubric", BASE, BONUS, WINDOW, BOND, 1)


@pytest.mark.parametrize("base,bonus", [(0, BONUS), (-1, BONUS), (BASE, -1)])
def test_create_rejects_bad_pay_values(funded, direct_alice, direct_bob, base, bonus):
    c = funded
    with pytest.raises(Exception, match="must"):
        c.create(direct_alice, direct_bob, base=base, bonus=bonus)


def test_create_rejects_liability_over_cap(funded, direct_alice, direct_bob):
    c = funded
    with pytest.raises(Exception, match="Liability exceeds allowed bound"):
        c.create(direct_alice, direct_bob, base=10**30, bonus=10**30)


@pytest.mark.parametrize("window", [59, 604801, 0, -1])
def test_create_rejects_bad_appeal_window(funded, direct_alice, direct_bob, window):
    c = funded
    with pytest.raises(Exception, match="Appeal window"):
        c.create(direct_alice, direct_bob, window=window)


def test_create_rejects_bond_over_liability(funded, direct_alice, direct_bob):
    c = funded
    with pytest.raises(Exception, match="Appeal bond exceeds maximum liability"):
        c.create(direct_alice, direct_bob, bond=MAX_LIABILITY + 1)


@pytest.mark.parametrize("count", [0, 5, -1])
def test_create_rejects_bad_tranche_count(funded, direct_alice, direct_bob, count):
    c = funded
    with pytest.raises(Exception, match="tranche"):
        c.create(direct_alice, direct_bob, tranches=count)


@pytest.mark.parametrize("role,rubric", [("", "rubric"), ("role", "")])
def test_create_rejects_empty_role_or_rubric(funded, direct_alice, direct_bob, role, rubric):
    c = funded
    with pytest.raises(Exception, match="required"):
        c.create(direct_alice, direct_bob, role=role, rubric=rubric)


@pytest.mark.parametrize("count", [1, 2, 3, 4])
def test_tranche_split_conserves_max_liability(funded, direct_alice, direct_bob, count):
    c = funded
    aid = c.create(direct_alice, direct_bob, tranches=count)
    agreement = c.agreement(aid)
    bases = [int(x) for x in agreement["tranche_bases"]]
    bonuses = [int(x) for x in agreement["tranche_bonuses"]]
    maxima = [int(x) for x in agreement["tranche_maxima"]]
    assert sum(bases) == BASE
    assert sum(bonuses) == BONUS
    assert sum(maxima) == MAX_LIABILITY
    assert all(maxima[i] == bases[i] + bonuses[i] for i in range(count))


def test_two_agreements_lock_the_sum(funded, direct_alice, direct_bob):
    c = funded
    c.create(direct_alice, direct_bob)
    c.create(direct_alice, direct_bob, base=20 * GEN, bonus=5 * GEN)
    state = c.vault_state()
    assert state["locked_payroll_escrows"] == str(MAX_LIABILITY + 25 * GEN)
    assert state["vault_custody_balance"] == str(MAX_LIABILITY + 25 * GEN)
    assert c.invariant() is True


def test_agreement_count_view(funded, direct_alice, direct_bob):
    c = funded
    assert c.c.get_agreement_count() == 0
    c.create(direct_alice, direct_bob)
    c.create(direct_alice, direct_bob, base=20 * GEN, bonus=5 * GEN)
    assert c.c.get_agreement_count() == 2


def test_submit_rejects_non_worker(funded, direct_alice, direct_bob):
    c = funded
    aid = c.create(direct_alice, direct_bob)
    c.mock_evidence()
    c.vm.sender = direct_alice
    with pytest.raises(Exception, match="Only the worker"):
        c.c.submit_tranche(aid, 0, 40, "work", json.dumps([GOOD_URL]))


def test_submit_rejects_duplicate_tranche(funded, direct_alice, direct_bob):
    c = funded
    aid = c.create(direct_alice, direct_bob)
    c.mock_evidence()
    c.submit(direct_bob, aid)
    with pytest.raises(Exception, match="Tranche already submitted"):
        c.submit(direct_bob, aid)


def test_submit_rejects_out_of_range_index(funded, direct_alice, direct_bob):
    c = funded
    aid = c.create(direct_alice, direct_bob)
    c.mock_evidence()
    with pytest.raises(Exception, match="Tranche index out of range"):
        c.submit(direct_bob, aid, idx=1)


def test_submit_rejects_second_active_tranche(funded, direct_alice, direct_bob):
    c = funded
    aid = c.create(direct_alice, direct_bob, tranches=2)
    c.mock_evidence()
    c.submit(direct_bob, aid, idx=0)
    with pytest.raises(Exception, match="Another tranche is still active"):
        c.submit(direct_bob, aid, idx=1)


@pytest.mark.parametrize("hours", [0, -1, 721])
def test_submit_rejects_bad_hours(funded, direct_alice, direct_bob, hours):
    c = funded
    aid = c.create(direct_alice, direct_bob)
    c.mock_evidence()
    with pytest.raises(Exception, match="Hours"):
        c.submit(direct_bob, aid, hours=hours)


@pytest.mark.parametrize(
    "urls",
    [
        [],
        ["https://ipfs.io/ipfs/bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi"] * 4,
    ],
)
def test_submit_rejects_bad_url_count(funded, direct_alice, direct_bob, urls):
    c = funded
    aid = c.create(direct_alice, direct_bob)
    c.mock_evidence()
    with pytest.raises(Exception, match="1 to 3 evidence URLs"):
        c.submit(direct_bob, aid, urls=urls)


@pytest.mark.parametrize(
    "urls",
    [
        ["https://ipfs.io.evil.com/ipfs/bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi"],
        ["http://ipfs.io/ipfs/bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi"],
    ],
)
def test_submit_rejects_bad_urls(funded, direct_alice, direct_bob, urls):
    c = funded
    aid = c.create(direct_alice, direct_bob)
    c.mock_evidence()
    with pytest.raises(Exception, match="Evidence URL must"):
        c.submit(direct_bob, aid, urls=urls)


def test_submit_rejects_unfetchable_evidence(funded, direct_alice, direct_bob):
    c = funded
    aid = c.create(direct_alice, direct_bob)
    # Direct Mode's web render mock returns the body regardless of status, so an
    # empty body is used to model a page that renders no usable evidence.
    c.mock_evidence(body="")
    with pytest.raises(Exception, match="Evidence not fetchable"):
        c.submit(direct_bob, aid)
