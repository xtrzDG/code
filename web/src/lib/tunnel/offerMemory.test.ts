import { describe, expect, it } from "vitest";

import { exampleKeyOf, exampleRowKey, readDoneExamples, rememberDoneExample, type MemoryStorage } from "./offerMemory";

function memoryStorage(initial: Record<string, string> = {}): MemoryStorage & { values: Record<string, string> } {
  const values = { ...initial };
  return {
    values,
    getItem: (key) => values[key] ?? null,
    setItem: (key, value) => {
      values[key] = value;
    },
  };
}

describe("offer example memory", () => {
  it("tells example rows from the owner's own lines", () => {
    expect(exampleKeyOf(exampleRowKey("haircut"))).toBe("haircut");
    expect(exampleKeyOf("new-3")).toBeNull();
    expect(exampleKeyOf("starter-")).toBeNull();
  });

  it("remembers dealt-with examples per business", () => {
    const storage = memoryStorage();
    rememberDoneExample(storage, "business_1", "haircut");
    rememberDoneExample(storage, "business_1", "manicure");
    rememberDoneExample(storage, "business_1", "haircut");
    expect([...readDoneExamples(storage, "business_1")]).toEqual(["haircut", "manicure"]);
    expect(readDoneExamples(storage, "business_2").size).toBe(0);
  });

  it("reads a broken or foreign value as nothing remembered", () => {
    const storage = memoryStorage({ "aw_offer_examples_done:business_1": "{not json", "aw_offer_examples_done:business_2": '{"a":1}' });
    expect(readDoneExamples(storage, "business_1").size).toBe(0);
    expect(readDoneExamples(storage, "business_2").size).toBe(0);
    expect([...readDoneExamples(memoryStorage({ "aw_offer_examples_done:b": '["x", 3]' }), "b")]).toEqual(["x"]);
  });

  it("works without storage, and when storage refuses", () => {
    expect(readDoneExamples(null, "business_1").size).toBe(0);
    const refusing: MemoryStorage = {
      getItem: () => {
        throw new Error("blocked");
      },
      setItem: () => {
        throw new Error("quota");
      },
    };
    expect(readDoneExamples(refusing, "business_1").size).toBe(0);
    expect(() => rememberDoneExample(refusing, "business_1", "haircut")).not.toThrow();
  });
});
