/**
 * No test-version leftovers in what owners, staff and visitors read: no
 * server settings or "not set up on this server", no release jargon, no
 * "sandbox", no made-up Georgian or German sample data, no "not available
 * yet". Platform admin pages may name settings and releases; the legal
 * texts wait for a lawyer and are not checked here.
 */

import { describe, expect, it } from "vitest";

import { en } from "./messages/en";
import { it as italian } from "./messages/it";
import type { MessageTree } from "./translate";

type Leaf = { path: string; text: string };

function leaves(tree: MessageTree, prefix = ""): Leaf[] {
  return Object.entries(tree).flatMap(([key, value]) =>
    typeof value === "string" ? [{ path: `${prefix}${key}`, text: value }] : value ? leaves(value, `${prefix}${key}.`) : [],
  );
}

/** The platform admin's pages and the legal texts (owner action). */
const NOT_CHECKED = /^(admin[A-Za-z]*|dataTasks|providerCircuits|legalPages|cookieConsent|accessibility)\./;
const INDEXING_NOTE = /^dataTasks\.indexing\./;
/**
 * Texts that are right as they are: the development-only toast of a test
 * written to the log (outside production only, staff_providers.py), and an
 * exchange-rate source the prices really come from.
 */
const KEPT = new Set(["notifications.contacts.testSimulated", "publicPricing.rateSources.nbg"]);

function ownerLeaves(tree: MessageTree): Leaf[] {
  return leaves(tree).filter((leaf) => !KEPT.has(leaf.path) && (!NOT_CHECKED.test(leaf.path) || INDEXING_NOTE.test(leaf.path)));
}

const LEFTOVERS: readonly [string, RegExp][] = [
  ["a server setting", /\b[A-Z][A-Z0-9]{2,}_[A-Z0-9_]{2,}\b/],
  ["the server", /\bthis server\b|\bon the (platform's )?server\b|questo server|sul server/i],
  ["set up on the platform", /not (set up|configured) on this platform|non (è|sono) (ancora )?configurat[aei] su questa piattaforma/i],
  ["release jargon", /\b(release|rilascio)\b/i],
  ["sandbox", /\bsandbox\b|ambiente di prova/i],
  ["not available yet", /not available yet|non ancora disponibil/i],
  ["Georgian or German samples", /\bNino\b|Morgenrot|\+995|Bank of Georgia|\bTBC\b|cafe_batumi|in Georgia\b|outside Georgia|dalla Georgia|in Georgia,/],
];

describe("owner-visible texts of a finished product", () => {
  it.each([
    ["en", en],
    ["it", italian],
  ] as const)("carry no test-version leftovers (%s)", (_, tree) => {
    const found = ownerLeaves(tree).flatMap((leaf) =>
      LEFTOVERS.filter(([, pattern]) => pattern.test(leaf.text)).map(([kind]) => `${leaf.path}: ${kind}`),
    );
    expect(found).toEqual([]);
  });

  it("say plainly that something is not available, and point to support", () => {
    expect(en.share.notConfigured).toBe("The chat page is not available right now. Contact support.");
    expect(italian.share.notConfigured).toBe("La pagina della chat non è disponibile al momento. Contatta l'assistenza.");
    expect(en.auth.countryUnavailable).toBe("not available");
    expect(italian.auth.countryUnavailable).toBe("non disponibile");
  });

  it("name the landing demo a demo, with a privacy reminder", () => {
    expect(en.publicDemo.footer).toBe("Demo: nothing is booked for real · please don't share personal details");
    expect(italian.publicDemo.footer).toBe("Demo: nessuna prenotazione è reale · non condividere dati personali");
  });

  it("describe manual deposit confirmation neutrally, and a business being set up", () => {
    expect(en.deposits.settings.manual).not.toMatch(/not connected/);
    expect(italian.deposits.settings.manual).not.toMatch(/non è collegata/);
    expect(en.businesses.status.testing).toBe("Setting up");
    expect(italian.businesses.status.testing).toBe("In configurazione");
  });
});
