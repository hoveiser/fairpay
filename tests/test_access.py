import ast
import pathlib

import pytest

SRC = pathlib.Path("contracts/contract.py").read_text(encoding="utf-8")
TREE = ast.parse(SRC)


def _contract_class():
    return next(n for n in TREE.body if isinstance(n, ast.ClassDef) and n.name == "FairPay")


def test_storage_has_no_owner_or_admin_field():
    fields = [
        n.target.id
        for n in _contract_class().body
        if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name)
    ]
    assert "owner" not in fields
    assert "admin" not in fields
    assert "vault_custody_balance" in fields
    assert "token_balances" in fields


def test_no_owner_or_admin_override_methods():
    methods = [n.name for n in _contract_class().body if isinstance(n, ast.FunctionDef)]
    forbidden = ("owner", "admin", "override", "force", "set_band", "set_anchor",
                 "set_tier", "emergency", "emergency_withdraw")
    assert not [m for m in methods if any(f in m.lower() for f in forbidden)]


def test_only_consensus_methods_write_the_payroll_band():
    writers = set()
    for fn in [n for n in _contract_class().body if isinstance(n, ast.FunctionDef)]:
        for node in ast.walk(fn):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if (
                        isinstance(target, ast.Subscript)
                        and isinstance(target.slice, ast.Constant)
                        and target.slice.value == "payroll_band"
                    ):
                        writers.add(fn.name)
    assert writers == {"audit_work_period_live", "resolve_appeal_live"}


def test_no_employer_native_payout_path():
    # All custody movement is ledger based. There is no EthSend path that an
    # employer could point at the vault.
    assert "EthSend" not in SRC
    assert "gl_call_generic" not in SRC


def test_missing_audit_methods_are_not_present():
    methods = [n.name for n in _contract_class().body if isinstance(n, ast.FunctionDef)]
    assert "audit_work_period_live" in methods
    assert "resolve_appeal_live" in methods


def test_audit_is_permissionless(funded, direct_alice, direct_bob, direct_charlie):
    c = funded
    aid = c.create(direct_alice, direct_bob)
    c.mock_evidence()
    c.mock_audit(True, 80)
    c.submit(direct_bob, aid)
    c.vm.sender = direct_charlie
    assert c.c.audit_work_period_live(aid, 0) == 80
    assert c.tranche(aid)["status"] == "audited"


def test_settlement_is_permissionless(funded, direct_alice, direct_bob, direct_charlie):
    c = funded
    aid = c.create(direct_alice, direct_bob)
    c.mock_evidence()
    c.mock_audit(True, 80)
    c.submit(direct_bob, aid)
    c.audit(aid)
    c.add_time(121)
    c.vm.sender = direct_charlie
    rid = c.c.settle_agreement(aid)
    assert c.receipt(rid)["worker_payout"] == str(76 * 10**18)


def test_employer_and_third_party_get_the_same_consensus_result(funded, direct_alice, direct_bob, direct_charlie):
    c = funded
    c.deposit(direct_alice, 200 * 10**18)
    c.mock_evidence()
    c.mock_audit(True, 65)
    a1 = c.create(direct_alice, direct_bob)
    c.submit(direct_bob, a1)
    c.audit(a1, actor=direct_alice)
    a2 = c.create(direct_alice, direct_bob)
    c.submit(direct_bob, a2)
    c.audit(a2, actor=direct_charlie)
    assert c.tranche(a1)["delivery_anchor"] == 80
    assert c.tranche(a2)["delivery_anchor"] == 80
    assert c.tranche(a1)["payroll_band"] == c.tranche(a2)["payroll_band"]


def test_submit_is_worker_only(funded, direct_alice, direct_bob):
    c = funded
    aid = c.create(direct_alice, direct_bob)
    c.mock_evidence()
    c.vm.sender = direct_alice
    with pytest.raises(Exception, match="Only the worker"):
        c.c.submit_tranche(aid, 0, 40, "work", '[{"desc": "x", "url": "https://ipfs.io/ipfs/bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi"}]')


def test_recover_is_employer_only(funded, direct_alice, direct_bob):
    c = funded
    aid = c.create(direct_alice, direct_bob)
    with pytest.raises(Exception, match="Only the employer"):
        c.recover(direct_bob, aid)


def test_mutual_is_party_only(funded, direct_alice, direct_bob, direct_charlie):
    c = funded
    aid = c.create(direct_alice, direct_bob)
    with pytest.raises(Exception, match="Only a party"):
        c.mutual(direct_charlie, aid, 5000)
