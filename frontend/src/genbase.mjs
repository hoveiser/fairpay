// genbase calldata codec + minimal RLP, ported from genlayer_py.abi.calldata
// so the browser can build and read GenLayer `gen_call` payloads directly.
// Verified byte-for-byte against the Python SDK reference vectors.

const BITS_IN_TYPE = 3n;
const TYPE_SPECIAL = 0n, TYPE_PINT = 1n, TYPE_NINT = 2n, TYPE_BYTES = 3n,
      TYPE_STR = 4n, TYPE_ARR = 5n, TYPE_MAP = 6n;
const SPECIAL_NULL = 0n, SPECIAL_FALSE = 8n, SPECIAL_TRUE = 16n, SPECIAL_ADDR = 24n;

function uleb(buf, x) {
  x = BigInt.asUintN(64, x);
  if (x === 0n) { buf.push(0); return; }
  while (x > 0n) {
    let cur = Number(x & 0x7fn);
    x >>= 7n;
    if (x > 0n) cur |= 0x80;
    buf.push(cur);
  }
}

function impl(buf, v) {
  if (v === null || v === undefined) buf.push(Number(SPECIAL_NULL));
  else if (v === true) buf.push(Number(SPECIAL_TRUE));
  else if (v === false) buf.push(Number(SPECIAL_FALSE));
  else if (typeof v === "number" || typeof v === "bigint") {
    let n = BigInt(v);
    if (n >= 0n) uleb(buf, (n << BITS_IN_TYPE) | TYPE_PINT);
    else { n = -n - 1n; uleb(buf, (n << BITS_IN_TYPE) | TYPE_NINT); }
  } else if (typeof v === "string") {
    const b = new TextEncoder().encode(v);
    uleb(buf, (BigInt(b.length) << BITS_IN_TYPE) | TYPE_STR);
    for (const x of b) buf.push(x);
  } else if (v instanceof Uint8Array) {
    uleb(buf, (BigInt(v.length) << BITS_IN_TYPE) | TYPE_BYTES);
    for (const x of v) buf.push(x);
  } else if (Array.isArray(v)) {
    uleb(buf, (BigInt(v.length) << BITS_IN_TYPE) | TYPE_ARR);
    for (const x of v) impl(buf, x);
  } else if (typeof v === "object") {
    const keys = Object.keys(v).sort();
    uleb(buf, (BigInt(keys.length) << BITS_IN_TYPE) | TYPE_MAP);
    for (const k of keys) {
      const kb = new TextEncoder().encode(k);
      uleb(buf, BigInt(kb.length));
      for (const x of kb) buf.push(x);
      impl(buf, v[k]);
    }
  } else throw new Error("invalid type " + typeof v);
}

export function encode(x) { const buf = []; impl(buf, x); return Uint8Array.from(buf); }

export function decode(bytes) {
  let pos = 0;
  const mem = bytes;
  function readUleb() {
    let ret = 0n, off = 0n;
    for (;;) {
      const m = mem[pos++];
      ret |= BigInt(m & 0x7f) << off;
      off += 7n;
      if ((m & 0x80) === 0) break;
    }
    return ret;
  }
  function implD() {
    const code = readUleb();
    const typ = code & 0x7n;
    if (typ === TYPE_SPECIAL) {
      if (code === SPECIAL_NULL) return null;
      if (code === SPECIAL_FALSE) return false;
      if (code === SPECIAL_TRUE) return true;
      if (code === SPECIAL_ADDR) { const r = mem.slice(pos, pos + 20); pos += 20; return "0x" + toHex(r); }
      throw new Error("unknown special " + code);
    }
    const n = code >> BITS_IN_TYPE;
    if (typ === TYPE_PINT) return n;
    if (typ === TYPE_NINT) return -n - 1n;
    if (typ === TYPE_BYTES) { const r = mem.slice(pos, pos + Number(n)); pos += Number(n); return r; }
    if (typ === TYPE_STR) { const r = mem.slice(pos, pos + Number(n)); pos += Number(n); return new TextDecoder().decode(r); }
    if (typ === TYPE_ARR) { const a = []; for (let i = 0n; i < n; i++) a.push(implD()); return a; }
    if (typ === TYPE_MAP) { const d = {}; for (let i = 0n; i < n; i++) { const le = Number(readUleb()); const key = new TextDecoder().decode(mem.slice(pos, pos + le)); pos += le; d[key] = implD(); } return d; }
    throw new Error("invalid type " + typ);
  }
  return implD();
}

// RLP encode for a list of Uint8Array items (our gen_call data frame).
export function rlpList(items) {
  const parts = [];
  for (const it of items) {
    if (it.length === 1 && it[0] < 0x80) parts.push(Uint8Array.from([it[0]]));
    else if (it.length <= 55) parts.push(prefix(0x80 + it.length, it));
    else { const h = beBytes(it.length); parts.push(concat(Uint8Array.from([0xb7 + h.length, ...h]), it)); }
  }
  const payload = parts.reduce((a, b) => concat(a, b), new Uint8Array(0));
  if (payload.length <= 55) return prefix(0xc0 + payload.length, payload);
  const h = beBytes(payload.length);
  return concat(Uint8Array.from([0xf7 + h.length, ...h]), payload);
}
function prefix(p, body) { const o = new Uint8Array(body.length + 1); o[0] = p; o.set(body, 1); return o; }
function concat(a, b) { const o = new Uint8Array(a.length + b.length); o.set(a); o.set(b, a.length); return o; }
function beBytes(n) { const h = []; let x = n; while (x > 0) { h.unshift(x & 0xff); x = Math.floor(x / 256); } return h; }

export function toHex(u8) { return Array.from(u8).map(b => b.toString(16).padStart(2, "0")).join(""); }
export function fromHex(hex) { hex = hex.replace(/^0x/, ""); const o = new Uint8Array(hex.length / 2); for (let i = 0; i < o.length; i++) o[i] = parseInt(hex.substr(i * 2, 2), 16); return o; }

// Build the `data` field (0x-hex RLP) for a read call of method+args.
export function callData(method, args) {
  const obj = {};
  if (method != null) obj.method = method;
  if (args && args.length) obj.args = args;
  const cd = encode(obj);
  return "0x" + toHex(rlpList([cd, Uint8Array.from([0])]));
}
