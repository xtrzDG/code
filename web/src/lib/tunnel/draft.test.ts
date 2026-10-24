import { describe, expect, it } from "vitest";

import {
  browserStorage,
  clearDraft,
  DRAFT_KEY_PREFIX,
  EMPTY_DRAFT,
  isDraftEmpty,
  parseDraft,
  readDraft,
  serializeDraft,
  writeDraft,
  type CreateDraft,
  type DraftStorage,
} from "./draft";

function memoryStorage(): DraftStorage & { data: Map<string, string> } {
  const data = new Map<string, string>();
  return {
    data,
    getItem: (key) => data.get(key) ?? null,
    setItem: (key, value) => void data.set(key, value),
    removeItem: (key) => void data.delete(key),
  };
}

const failing: DraftStorage = {
  getItem: () => {
    throw new Error("denied");
  },
  setItem: () => {
    throw new Error("quota");
  },
  removeItem: () => {
    throw new Error("denied");
  },
};

const DRAFT: CreateDraft = {
  ...EMPTY_DRAFT,
  step: "place",
  name: "Salon Morgenrot",
  nicheKey: "beauty_salon",
  answers: { service_categories: { text: "", choices: ["hair"] } },
  countryCode: "DE",
  city: "Berlin",
  address: "Torstraße 1",
  languagesByCountry: { DE: ["de", "en"] },
  defaultByCountry: { DE: "de" },
  zoneByCountry: { DE: "Europe/Berlin" },
};

describe("create draft", () => {
  it("round-trips through storage, one per account", () => {
    const storage = memoryStorage();
    expect(writeDraft(storage, "user_1", DRAFT)).toBe(true);
    expect(readDraft(storage, "user_1")).toEqual(DRAFT);
    expect(readDraft(storage, "user_2")).toBeNull();
    expect([...storage.data.keys()]).toEqual([`${DRAFT_KEY_PREFIX}user_1`]);
    clearDraft(storage, "user_1");
    expect(readDraft(storage, "user_1")).toBeNull();
  });

  it("is not kept while nothing is typed", () => {
    const storage = memoryStorage();
    writeDraft(storage, "user_1", DRAFT);
    expect(isDraftEmpty(EMPTY_DRAFT)).toBe(true);
    expect(isDraftEmpty(DRAFT)).toBe(false);
    writeDraft(storage, "user_1", EMPTY_DRAFT);
    expect(storage.data.size).toBe(0);
  });

  it("survives storage that is missing or refuses", () => {
    expect(writeDraft(null, "user_1", DRAFT)).toBe(false);
    expect(writeDraft(failing, "user_1", DRAFT)).toBe(false);
    expect(readDraft(failing, "user_1")).toBeNull();
    expect(readDraft(null, "user_1")).toBeNull();
    expect(() => clearDraft(failing, "user_1")).not.toThrow();
    expect(() => clearDraft(null, "user_1")).not.toThrow();
  });

  it("reads anything broken or foreign as no draft", () => {
    expect(parseDraft(null)).toBeNull();
    expect(parseDraft("not json")).toBeNull();
    expect(parseDraft(JSON.stringify({ version: 99, draft: DRAFT }))).toBeNull();
    expect(parseDraft(JSON.stringify({ version: 1, draft: "x" }))).toBeNull();
    expect(parseDraft(JSON.stringify([1, 2]))).toBeNull();
  });

  it("drops unexpected fields one by one", () => {
    const raw = JSON.stringify({
      version: 1,
      draft: {
        step: "launch",
        name: 7,
        nicheKey: "restaurant",
        answers: { good: { text: "x", choices: ["a", 3] }, bad: { text: 1 }, worse: "x" },
        countryCode: "germany",
        city: "Berlin",
        languagesByCountry: { DE: ["de"], ES: [1], FR: "fr" },
        defaultByCountry: { DE: "de", ES: 2 },
        zoneByCountry: [],
      },
    });
    expect(parseDraft(raw)).toEqual({
      ...EMPTY_DRAFT,
      step: "business",
      nicheKey: "restaurant",
      answers: { good: { text: "x", choices: ["a"] } },
      city: "Berlin",
      languagesByCountry: { DE: ["de"] },
      defaultByCountry: { DE: "de" },
    });
  });

  it("reads back what it writes", () => {
    expect(parseDraft(serializeDraft(DRAFT))).toEqual(DRAFT);
    expect(parseDraft(JSON.stringify({ version: 1, draft: { answers: [] } }))).toEqual(EMPTY_DRAFT);
  });

  it("finds no browser storage outside a browser", () => {
    expect(browserStorage()).toBeNull();
  });
});
