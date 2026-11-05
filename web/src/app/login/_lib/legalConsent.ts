/**
 * The code step's acceptance line ("By continuing, you accept the {terms}
 * and ... the {privacy}"): its text cut into plain parts and the two
 * documents the reader can open, so each language keeps its own word order.
 */

export type LegalDocumentKind = "terms" | "privacy" | "cookies";

export type ConsentPart = { kind: "text"; text: string } | { kind: "document"; document: LegalDocumentKind };

const PLACEHOLDER = /\{(terms|privacy)\}/g;

/** "A {terms} B {privacy}." -> [text A, terms, text B, privacy, text "."]. */
export function splitConsentLine(line: string): ConsentPart[] {
  const parts: ConsentPart[] = [];
  let last = 0;
  for (const match of line.matchAll(PLACEHOLDER)) {
    const start = match.index;
    if (start > last) {
      parts.push({ kind: "text", text: line.slice(last, start) });
    }
    parts.push({ kind: "document", document: match[1] as LegalDocumentKind });
    last = start + match[0].length;
  }
  if (last < line.length) {
    parts.push({ kind: "text", text: line.slice(last) });
  }
  return parts;
}

/** The terms version to send with the code: only the one the line showed. */
export function acceptedTermsBody(termsVersion: string | null): { accepted_terms_version?: string } {
  return termsVersion ? { accepted_terms_version: termsVersion } : {};
}

/** The terms and privacy policy versions the code step names. */
export interface ConsentVersions {
  termsVersion: string | null;
  privacyVersion: string | null;
}

/**
 * Each version from `preferred`, else from `fallback`. The code step keeps
 * the versions it named from the moment the code was sent, so the sign-in
 * options reloading under it (the country list arriving late changes the
 * guessed country) neither hides the line, closes an open document nor
 * changes the version accepted with the code: a resend prefers the
 * versions it sees, and versions that arrive after the code was sent only
 * fill in what the step did not know yet.
 */
export function preferConsentVersions(preferred: ConsentVersions, fallback: ConsentVersions | null): ConsentVersions {
  return {
    termsVersion: preferred.termsVersion ?? fallback?.termsVersion ?? null,
    privacyVersion: preferred.privacyVersion ?? fallback?.privacyVersion ?? null,
  };
}
