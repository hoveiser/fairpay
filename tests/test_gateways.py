# v0.4.1 multi-gateway evidence, Direct Mode.
#
# The point of the allowlist is that availability improves but integrity does
# NOT depend on which gateway answered: submit seals the sha256 of the cleaned
# fetched text, and resolve re-fetches the stored URL and re-hashes it. These
# tests pin that: (1) every allowed gateway is accepted with a valid CID, (2)
# lookalike/unknown gateways and every URL-attack form are rejected before any
# state change, (3) the seal is identical across gateways for the same bytes,
# and (4) different bytes for the same stored URL (the cross-gateway variance
# the allowlist makes possible) are caught as MISMATCH with zero pay.
import json
import re

import pytest

from conftest import GEN, EVIDENCE_V1, EVIDENCE_V2, addr

T0 = "2026-08-30T12:00:00Z"
CID = "bafkreidwkl2tdyhpeij4es7ng23qiexzxn5nq2ae2ckf6nmtsahrsit5zq"
ALLOWED_HOSTS = ("gateway.pinata.cloud", "ipfs.io", "dweb.link", "w3s.link")


def _setup(fp, direct_vm, direct_alice, direct_bob):
    direct_vm.warp(T0)
    c = fp(budget=10 * GEN)
    c.set_time(T0)
    return c


def _items(url):
    return json.dumps([{"desc": "progress note", "url": url, "impact": "small"}])


@pytest.mark.parametrize("host", ALLOWED_HOSTS)
def test_each_allowed_gateway_accepted(direct_vm, fp, direct_alice, direct_bob, host):
    c = _setup(fp, direct_vm, direct_alice, direct_bob)
    jid = c.create_job(direct_alice, addr(direct_bob))
    direct_vm.clear_mocks()
    c.mock_evidence(EVIDENCE_V1, pattern=re.escape(host))
    pid = c.submit(direct_bob, jid, 4, _items("https://" + host + "/ipfs/" + CID))
    p = c.period(pid)
    assert p["status"] == "submitted"
    assert p["evidence_hash"] not in (None, "", "FETCH_FAILED")


@pytest.mark.parametrize("bad", [
    "https://evil.example/ipfs/" + CID,                       # unknown gateway
    "https://ipfs.io.evil.com/ipfs/" + CID,                   # lookalike host
    "https://ipfs.io@evil.com/ipfs/" + CID,                   # userinfo trick
    "http://ipfs.io/ipfs/" + CID,                             # wrong scheme
    "https://ipfs.io:8443/ipfs/" + CID,                       # port
    "https://ipfs.io/ipfs/" + CID + "?download=1",            # query
    "https://ipfs.io/ipfs/" + CID + "#frag",                  # fragment
    "https://ipfs.io/ipfs/" + CID + "/extra",                 # extra segment
    "https://ipfs.io/ipfs/../" + CID,                         # traversal
])
def test_attack_gateway_urls_rejected_before_state_change(direct_vm, fp, direct_alice, direct_bob, bad):
    c = _setup(fp, direct_vm, direct_alice, direct_bob)
    jid = c.create_job(direct_alice, addr(direct_bob))
    direct_vm.clear_mocks()
    c.mock_evidence(EVIDENCE_V1)          # content would serve fine; URL must fail first
    with pytest.raises(AssertionError, match="canonical IPFS"):
        c.submit(direct_bob, jid, 4, _items(bad))
    # no state change: the item URL assert runs before any period is created
    assert c.job(jid)["open_period"] is None
    assert c.job(jid)["period_ids"] == []
    assert c.reserved(jid) == 0
    assert c.balance(jid) == 10 * GEN


def test_seal_is_gateway_independent(direct_vm, fp, direct_alice, direct_bob):
    # The same bytes served by two different allowed gateways must produce the
    # SAME sealed content hash: integrity is a property of the content, not of
    # which gateway answered. This is exactly why the allowlist is safe.
    budget = 20 * GEN
    direct_vm.warp(T0)
    c = fp(budget=budget)
    c.set_time(T0)
    j1 = c.create_job(direct_alice, addr(direct_bob), budget=budget)
    j2 = c.create_job(direct_alice, addr(direct_bob), budget=budget)
    direct_vm.clear_mocks()
    c.mock_evidence(EVIDENCE_V1, pattern=r"gateway\.pinata\.cloud")
    c.mock_evidence(EVIDENCE_V1, pattern=r"dweb\.link")
    p1 = c.submit(direct_bob, j1, 4, _items("https://gateway.pinata.cloud/ipfs/" + CID))
    p2 = c.submit(direct_bob, j2, 4, _items("https://dweb.link/ipfs/" + CID))
    h1 = c.period(p1)["evidence_hash"]
    h2 = c.period(p2)["evidence_hash"]
    assert h1 == h2
    assert h1 != "FETCH_FAILED"


def test_same_cid_different_bytes_across_gateways_caught(direct_vm, fp, direct_alice, direct_bob):
    # Submit seals against the bytes one gateway served for the CID. When the
    # stored URL returns DIFFERENT bytes at audit time (what happens when a
    # gateway injects an HTML wrapper or resizes content for the same CID), the
    # sealed-hash comparison must catch it and pay zero, before any LLM call.
    c = _setup(fp, direct_vm, direct_alice, direct_bob)
    jid = c.create_job(direct_alice, addr(direct_bob))
    direct_vm.clear_mocks()
    c.mock_evidence(EVIDENCE_V1, pattern=r"dweb\.link")
    pid = c.submit(direct_bob, jid, 4, _items("https://dweb.link/ipfs/" + CID))
    sealed = c.period(pid)["evidence_hash"]
    assert sealed not in (None, "", "FETCH_FAILED")
    # the same stored URL now returns different bytes for the same CID
    direct_vm.clear_mocks()
    c.mock_evidence(EVIDENCE_V2, pattern=r"dweb\.link")
    c.mock_tier("HIGH")                   # must be irrelevant: hash check precedes LLM
    c.resolve(pid)
    p = c.period(pid)
    assert p["tier"] == "MISMATCH"
    assert p["pay"] == 0
    assert c.sends == []                 # nothing paid out
    c.assert_invariant(jid)
