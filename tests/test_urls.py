import pytest

from conftest import GOOD_URL

CID = "bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi"
COMMIT = "a" * 40

VALID = [
    "https://gateway.pinata.cloud/ipfs/" + CID,
    "https://ipfs.io/ipfs/" + CID,
    "https://dweb.link/ipfs/" + CID,
    "https://w3s.link/ipfs/" + CID,
    "https://raw.githubusercontent.com/hoveiser/fairpay/" + COMMIT + "/docs/evidence.txt",
    GOOD_URL,
]

INVALID = [
    "https://ipfs.io.evil.com/ipfs/" + CID,
    "https://ipfs.io@evil.com/ipfs/" + CID,
    "https://ipfs.io:443/ipfs/" + CID,
    "http://ipfs.io/ipfs/" + CID,
    "https://ipfs.io/ipfs/" + CID + "/extra",
    "https://ipfs.io/ipfs/" + CID + "?download=1",
    "https://ipfs.io/ipfs/" + CID + "#fragment",
    "https://ipfs.io/ipfs/Qm" + "0" * 44,
    "https://ipfs.io/ipfs/../../etc/passwd",
    "https://" + CID + ".ipfs.dweb.link/",
    "https://raw.githubusercontent.com/hoveiser/fairpay/main/docs/evidence.txt",
    "https://raw.githubusercontent.com/hoveiser/fairpay/" + COMMIT + "/docs/../secret.txt",
    "https://raw.githubusercontent.com/hoveiser/fairpay/" + COMMIT + "/docs//evidence.txt",
    "https://raw.githubusercontent.com/hoveiser/fairpay/" + COMMIT + "/docs/evidence.txt/",
    "https://raw.githubusercontent.com/hoveiser/fairpay/" + COMMIT + "/docs/evidence.txt?raw=1",
    "https://ipfs.io/ipfs/" + CID + "x" * 500,
    "",
    "not a url",
]


@pytest.mark.parametrize("url", VALID)
def test_valid_immutable_urls_are_accepted(funded, direct_alice, direct_bob, url):
    c = funded
    aid = c.create(direct_alice, direct_bob)
    c.mock_evidence(pattern=r".*")
    c.submit(direct_bob, aid, urls=[url])
    assert c.tranche(aid)["status"] == "submitted"
    assert c.tranche(aid)["evidence_urls"] == [url]


@pytest.mark.parametrize("url", INVALID)
def test_invalid_urls_are_rejected(funded, direct_alice, direct_bob, url):
    c = funded
    aid = c.create(direct_alice, direct_bob)
    c.mock_evidence(pattern=r".*")
    with pytest.raises(Exception, match="URL not allowed"):
        c.submit(direct_bob, aid, urls=[url])


def test_multiple_valid_urls_are_sealed_together(funded, direct_alice, direct_bob):
    c = funded
    aid = c.create(direct_alice, direct_bob)
    c.mock_evidence(pattern=r".*")
    urls = [VALID[1], VALID[4]]
    c.submit(direct_bob, aid, urls=urls)
    assert c.tranche(aid)["evidence_urls"] == urls
    # Two URLs produce two concatenated sha256 digests.
    assert len(c.tranche(aid)["evidence_hash"].split("|")) == 2


def test_non_string_url_is_rejected(funded, direct_alice, direct_bob):
    c = funded
    aid = c.create(direct_alice, direct_bob)
    c.mock_evidence(pattern=r".*")
    c.vm.sender = direct_bob
    with pytest.raises(Exception, match="URL not allowed"):
        c.c.submit_tranche(aid, 0, 40, "work", '[123]')
