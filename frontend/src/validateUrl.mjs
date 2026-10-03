// Faithful client-side port of the v0.4.1 contract URL gate in
// contracts/contract.py: _is_content_addressed_url(). The decision here uses
// the SAME two anchored regexes and the SAME length cap as the on-chain code,
// so what the UI shows is exactly what submit_period enforces before any state
// change. The extra `explain()` helper only produces human-readable reasons for
// the rejected cases; it never changes the accept/reject decision.

export const GATEWAY_HOSTS = ["gateway.pinata.cloud", "ipfs.io", "dweb.link", "w3s.link"];
export const MAX_URL_LEN = 500;

// Same as _GATEWAY_RE: only these hosts, only the /ipfs/<single-segment> path.
const GATEWAY_RE = /^https:\/\/(?:gateway\.pinata\.cloud|ipfs\.io|dweb\.link|w3s\.link)\/ipfs\/([^/]+)$/;
// Same as _CID_RE: CIDv0 "Qm..." (46 base58btc chars) or CIDv1 "b..." base32.
const CID_RE = /^(Qm[1-9A-HJ-NP-Za-km-z]{44}|b[a-z2-7]{20,})$/;

export function isContentAddressedUrl(url) {
  if (typeof url !== "string") return false;
  if (url.length > MAX_URL_LEN) return false;
  const m = GATEWAY_RE.exec(url);
  if (!m) return false;
  return CID_RE.test(m[1]);
}

// Stepwise diagnosis for the UI. Returns {ok, steps:[{label, pass, detail}]}.
export function explain(url) {
  const steps = [];
  const push = (label, pass, detail) => steps.push({ label, pass, detail });

  push("Non-empty input", url.length > 0, url.length ? "" : "Type an IPFS evidence URL");

  push(
    `Length <= ${MAX_URL_LEN}`,
    url.length <= MAX_URL_LEN,
    `${url.length} chars`
  );

  // Parse scheme + authority so we can call out lookalike / userinfo / port.
  let parsed = null;
  try {
    parsed = new URL(url);
  } catch {
    parsed = null;
  }

  if (!parsed) {
    push("Absolute https:// URL", false, "Could not parse as a URL");
    return { ok: false, steps, cid: null };
  }

  push("Scheme is https", parsed.protocol === "https:", `scheme: ${parsed.protocol.replace(":", "") || "(none)"}`);
  push("No userinfo (user:pass@host)", !parsed.username && !parsed.password, parsed.username ? "contains credentials before @" : "clean");
  push("No explicit port", !parsed.port, parsed.port ? `port :${parsed.port}` : "default 443");

  const host = parsed.hostname.toLowerCase();
  const hostExact = GATEWAY_HOSTS.includes(host);
  // Detect lookalike: host ends with an allowed host but is not equal to it.
  const lookalike = !hostExact && GATEWAY_HOSTS.some((h) => host.endsWith("." + h) || host.endsWith(h) && host !== h);
  push(
    `Host in allowlist`,
    hostExact,
    hostExact
      ? `${host} (allowed)`
      : lookalike
        ? `REJECTED lookalike: ${host} is not exactly one of the 4 allowed hosts`
        : `${host} is not one of the 4 allowed hosts`
  );

  push(
    "Path is exactly /ipfs/<CID>",
    /^\/ipfs\/[^/]+$/.test(parsed.pathname),
    `path: ${parsed.pathname || "/"}`
  );
  push("No query string", !parsed.search, parsed.search ? `query: ${parsed.search}` : "none");
  push("No fragment", !parsed.hash, parsed.hash ? `fragment: ${parsed.hash}` : "none");

  const cid = parsed.pathname.startsWith("/ipfs/") ? decodeURIComponent(parsed.pathname.slice(6)) : null;
  const cidValid = cid ? CID_RE.test(cid) : false;
  push(
    "Content address is a valid CID",
    cidValid,
    cid ? (cidValid ? `${cid.length > 24 ? cid.slice(0, 12) + "..." + cid.slice(-6) : cid} (CIDv${cid.startsWith("Qm") ? "0" : "1"})` : `${cid} is not a valid CIDv0/v1`) : "no CID segment"
  );

  return { ok: isContentAddressedUrl(url), steps, cid };
}
