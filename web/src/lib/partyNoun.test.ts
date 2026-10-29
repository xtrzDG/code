import { describe, expect, it } from "vitest";

import { en } from "@/i18n/messages/en";
import { it as italian } from "@/i18n/messages/it";
import { createTranslator } from "@/i18n/translate";

import { PARTY_COUNT_KEYS, PARTY_LABEL_KEYS, partyNounFor, resourceKindOf } from "./partyNoun";

describe("who a booking is for", () => {
  it("speaks of guests at tables and rooms, clients of masters, bays and cars, participants of arenas and slots", () => {
    expect(partyNounFor("table")).toBe("guests");
    expect(partyNounFor("room")).toBe("guests");
    expect(partyNounFor("staff")).toBe("clients");
    expect(partyNounFor("bay")).toBe("clients");
    expect(partyNounFor("vehicle")).toBe("clients");
    expect(partyNounFor("arena")).toBe("participants");
    expect(partyNounFor("slot")).toBe("participants");
  });

  it("falls back to the niche's kind, then to guests", () => {
    expect(partyNounFor(null, "staff")).toBe("clients");
    expect(partyNounFor(undefined, null)).toBe("guests");
    expect(partyNounFor("table", "staff")).toBe("guests");
  });

  it("finds the kind of a listed resource", () => {
    const resources = [{ id: "nino", kind: "staff" as const }];
    expect(resourceKindOf(resources, "nino")).toBe("staff");
    expect(resourceKindOf(resources, "gone")).toBeNull();
    expect(resourceKindOf(resources, null)).toBeNull();
  });

  it("reads '1 cliente' in a salon, never '1 ospite'", () => {
    const tIt = createTranslator("it", italian, en);
    expect(tIt.tp(PARTY_COUNT_KEYS.clients, 1)).toBe("1 cliente");
    expect(tIt.tp(PARTY_COUNT_KEYS.clients, 3)).toBe("3 clienti");
    expect(tIt.tp(PARTY_COUNT_KEYS.guests, 5)).toBe("5 ospiti");
    expect(tIt.t(PARTY_LABEL_KEYS.clients)).toBe("Clienti");
    expect(tIt.tp(PARTY_COUNT_KEYS.participants, 8)).toBe("8 partecipanti");
    expect(createTranslator("en", en, en).tp(PARTY_COUNT_KEYS.clients, 2)).toBe("2 clients");
  });
});
