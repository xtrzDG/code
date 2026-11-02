/**
 * The server's record of every cookie choice (ePrivacy art. 5(3), the
 * Garante's cookie guidelines of 10 June 2021: a consent must be provable):
 * one JSON line on the cabinet server's log per answer, with the choice,
 * the version of the question, when, and the answer's pseudonymous receipt
 * id, the one the visitor's `aw_consent` cookie carries
 * (consentCookie.ts). Nothing about who: no address, page, browser or
 * account. The log is kept as long as the hosting keeps the web service's
 * logs (docs: the owner keeps them for the consent's six months and after).
 */

import type { ConsentChoice } from "./consentCookie";

const CONSENT_LOG_EVENT = "cookie_consent";

interface ConsentRecord {
  choice: ConsentChoice;
  version: string;
  consentId: string;
  /** When the answer was given (ISO 8601, UTC). */
  at: string;
}

type LineWriter = (line: string) => void;

function writeLine(line: string): void {
  process.stdout.write(`${line}\n`);
}

/** One line for one answer. */
export function logConsent(record: ConsentRecord, write: LineWriter = writeLine): void {
  write(
    JSON.stringify({
      event: CONSENT_LOG_EVENT,
      choice: record.choice,
      version: record.version,
      consent_id: record.consentId,
      at: record.at,
    }),
  );
}
