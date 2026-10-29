import { describe, expect, it } from "vitest";

import { SECURITY_TXT_FIELDS, securityContactEmail, securityTxt } from "./securityTxt";

const production = { SITE_URL: "https://app.example.com", SECURITY_CONTACT_EMAIL: "security@example.com" };

function fieldLines(text: string): string[] {
  return text.split("\n").filter((line) => line !== "" && !line.startsWith("#"));
}

describe("security.txt", () => {
  it("names the production mailbox first and the canonical address of the file", () => {
    const lines = fieldLines(securityTxt(new Headers({ host: "evil.example" }), production));

    expect(lines[0]).toBe("Contact: mailto:security@example.com");
    expect(lines[1]).toBe("Contact: https://github.com/xtrzDG/code/security/advisories/new");
    expect(lines.at(-1)).toBe("Canonical: https://app.example.com/.well-known/security.txt");
    expect(lines).toContain("Policy: https://github.com/xtrzDG/code/blob/main/SECURITY.md");
    expect(lines.filter((line) => line.startsWith("Expires: "))).toHaveLength(1);
  });

  it("keeps the advisory contact and the request's own address without configuration", () => {
    const text = securityTxt(new Headers({ host: "internal:3000", "x-forwarded-host": "cabinet.example.org", "x-forwarded-proto": "https" }), {});

    expect(text).not.toContain("mailto:");
    expect(text).toContain(SECURITY_TXT_FIELDS);
    expect(text).toMatch(/^Canonical: https:\/\/cabinet\.example\.org\/\.well-known\/security\.txt$/m);
    expect(text.endsWith("\n")).toBe(true);
  });

  it("accepts only one plain mailbox", () => {
    expect(securityContactEmail({ SECURITY_CONTACT_EMAIL: "  security@example.com " })).toBe("security@example.com");
    for (const value of ["", "security", "a@b", "security@example.com\nContact: https://evil.example", "a@example.com, b@example.com", "mailto:a@example.com"]) {
      expect(securityContactEmail({ SECURITY_CONTACT_EMAIL: value })).toBeNull();
    }
    expect(securityContactEmail({})).toBeNull();
  });

  it("is renewed before it expires and never more than a year ahead", () => {
    const expires = /^Expires: (.+)$/m.exec(SECURITY_TXT_FIELDS)?.[1] ?? "";
    const remainingDays = (Date.parse(expires) - Date.now()) / 86_400_000;

    expect(remainingDays).toBeGreaterThan(30);
    expect(remainingDays).toBeLessThanOrEqual(366);
  });
});
