import { describe, expect, it } from "vitest";

import { en } from "@/i18n/messages/en";
import { ka } from "@/i18n/messages/ka";
import { ru } from "@/i18n/messages/ru";
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

  it("reads '1 клиент' in a salon, never '1 гость'", () => {
    const tRu = createTranslator("ru", ru, en);
    expect(tRu.tp(PARTY_COUNT_KEYS.clients, 1)).toBe("1 клиент");
    expect(tRu.tp(PARTY_COUNT_KEYS.clients, 3)).toBe("3 клиента");
    expect(tRu.tp(PARTY_COUNT_KEYS.guests, 5)).toBe("5 гостей");
    expect(tRu.t(PARTY_LABEL_KEYS.clients)).toBe("Клиентов");
    const tKa = createTranslator("ka", ka, en);
    expect(tKa.tp(PARTY_COUNT_KEYS.participants, 8)).toBe("8 მონაწილე");
    expect(createTranslator("en", en, en).tp(PARTY_COUNT_KEYS.clients, 2)).toBe("2 clients");
  });
});
