// Live reads against the deployed FairPay contract on StudioNet, straight from
// the browser. studio.genlayer.com/api echoes Access-Control-Allow-Origin for
// local origins, so no proxy is required. Payloads are built with the genbase
// codec (validated byte-for-byte against the Python SDK) and responses decoded
// the same way, so these numbers are the real on-chain state, not a mock.

import { callData, decode, fromHex } from "./genbase.mjs";

export const CONTRACT_ADDRESS = "0xb16d9670A39e9eF22641312c1bFDE5E4e9673AF4";
export const RPC_URL = "https://studio.genlayer.com/api";
export const EXPLORER_URL = "https://explorer-studio.genlayer.com";
// Reads are sender-independent; a neutral public account is used to build the
// frame. No key is involved and nothing is signed.
const SENDER = "0x0000000000000000000000000000000000000000";

async function genCall(method, args) {
  const body = {
    jsonrpc: "2.0",
    id: 1,
    method: "gen_call",
    params: [
      {
        type: "read",
        to: CONTRACT_ADDRESS,
        from: SENDER,
        data: callData(method, args),
        transaction_hash_variant: "latest-nonfinal",
      },
    ],
  };
  const res = await fetch(RPC_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const json = await res.json();
  if (json.error) throw new Error(json.error.message || JSON.stringify(json.error));
  return decode(fromHex(json.result));
}

export async function readLiveState(jobId) {
  const [balance, reserved, jobJson] = await Promise.all([
    genCall("contract_balance", []),
    genCall("reserved_liability", [Number(jobId)]),
    genCall("get_job", [Number(jobId)]),
  ]);
  const job = JSON.parse(jobJson);
  return {
    jobId: Number(jobId),
    contractBalanceAtto: BigInt(balance),
    reservedAtto: BigInt(reserved),
    jobBudgetAtto: BigInt(job.budget),
    job,
  };
}
