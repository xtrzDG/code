/**
 * The cabinet's /.well-known/security.txt (RFC 9116): where to report a
 * vulnerability. Every deployment publishes SECURITY_TXT_FIELDS; production
 * puts its security mailbox (SECURITY_CONTACT_EMAIL) first and names the
 * file's own address (Canonical: SITE_URL, else the address the request came
 * in on), so a copy served anywhere else is recognised as one.
 *
 * tests/legal/test_security_documents.py reads SECURITY_TXT_FIELDS and fails
 * 30 days before Expires: renew it then, at most a year ahead.
 */

import { siteOrigin } from "@/server/siteOrigin";

const SECURITY_TXT_PATH = "/.well-known/security.txt";

export const SECURITY_TXT_FIELDS = `Contact: https://github.com/xtrzDG/code/security/advisories/new
Expires: 2027-07-01T00:00:00Z
Preferred-Languages: en, ru, ka
Policy: https://github.com/xtrzDG/code/blob/main/SECURITY.md`;

/** One mailbox: no spaces, line breaks or a second address can be smuggled into the file. */
const MAILBOX_PATTERN = /^[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$/;

/** SECURITY_CONTACT_EMAIL when it is one plain e-mail address, else null. */
export function securityContactEmail(env: Record<string, string | undefined> = process.env): string | null {
  const value = env.SECURITY_CONTACT_EMAIL?.trim() ?? "";
  return MAILBOX_PATTERN.test(value) ? value : null;
}

export function securityTxt(
  requestHeaders: Pick<Headers, "get">,
  env: Record<string, string | undefined> = process.env,
): string {
  const mailbox = securityContactEmail(env);
  return [
    "# Assistant Workshop: how to report a security vulnerability (RFC 9116).",
    "# Please read the policy first; do not report through public issues.",
    ...(mailbox ? [`Contact: mailto:${mailbox}`] : []),
    SECURITY_TXT_FIELDS,
    `Canonical: ${siteOrigin(requestHeaders, env)}${SECURITY_TXT_PATH}`,
    "",
  ].join("\n");
}
