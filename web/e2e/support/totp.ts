/**
 * An authenticator app inside the tests: RFC 6238 codes (HMAC-SHA1, six
 * digits, 30-second steps), the defaults of every common app and of the
 * API. A code works once, so a test that needs another one waits for the
 * next step.
 */

import { createHmac } from "node:crypto";

const BASE32_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
export const TOTP_STEP_MS = 30_000;

function base32Bytes(secret: string): Buffer {
  const clean = secret.replace(/[\s=]/g, "").toUpperCase();
  let bits = "";
  for (const character of clean) {
    const value = BASE32_ALPHABET.indexOf(character);
    if (value < 0) {
      throw new Error(`Not a base32 key: ${secret}`);
    }
    bits += value.toString(2).padStart(5, "0");
  }
  const bytes: number[] = [];
  for (let index = 0; index + 8 <= bits.length; index += 8) {
    bytes.push(Number.parseInt(bits.slice(index, index + 8), 2));
  }
  return Buffer.from(bytes);
}

/** The step a moment falls in (Unix time / 30 s). */
export function totpStep(atMs: number = Date.now()): number {
  return Math.floor(atMs / TOTP_STEP_MS);
}

/** The six digits an app shows during `step` for this key (spaces allowed). */
export function totpCode(secret: string, step: number = totpStep()): string {
  const counter = Buffer.alloc(8);
  counter.writeBigUInt64BE(BigInt(step));
  const digest = createHmac("sha1", base32Bytes(secret)).update(counter).digest();
  const offset = digest[digest.length - 1]! & 0x0f;
  const value = digest.readUInt32BE(offset) & 0x7fffffff;
  return String(value % 1_000_000).padStart(6, "0");
}

/**
 * A code of a step later than `usedStep` (the API takes each step once):
 * waits for the next step when needed. Returns the code and its step.
 */
export async function freshTotpCode(secret: string, usedStep: number | null): Promise<{ code: string; step: number }> {
  let step = totpStep();
  if (usedStep !== null && step <= usedStep) {
    const nextStepAt = (usedStep + 1) * TOTP_STEP_MS;
    await new Promise((resolve) => setTimeout(resolve, nextStepAt - Date.now() + 250));
    step = totpStep();
  }
  return { code: totpCode(secret, step), step };
}
