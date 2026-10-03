import { describe, expect, it } from "vitest";

import { readDetailsChoice, startsOpen, writeDetailsChoice, type ChoiceStorage } from "./technicalDetails";

function memory(): ChoiceStorage {
  const values = new Map<string, string>();
  return { getItem: (key) => values.get(key) ?? null, setItem: (key, value) => void values.set(key, value) };
}

describe("technical details", () => {
  it("start open only for platform admins on a wide screen", () => {
    expect(startsOpen(null, true, true)).toBe(true);
    expect(startsOpen(null, true, false)).toBe(false);
    expect(startsOpen(null, false, true)).toBe(false);
  });

  it("follow the person's own last choice", () => {
    expect(startsOpen("open", false, false)).toBe(true);
    expect(startsOpen("closed", true, true)).toBe(false);
  });

  it("remember the choice per person", () => {
    const storage = memory();
    writeDetailsChoice(storage, "user_1", "open");
    expect(readDetailsChoice(storage, "user_1")).toBe("open");
    expect(readDetailsChoice(storage, "user_2")).toBeNull();
  });

  it("read nothing from a missing or refusing storage, or a foreign value", () => {
    expect(readDetailsChoice(null, "user_1")).toBeNull();
    const refusing: ChoiceStorage = {
      getItem: () => {
        throw new Error("blocked");
      },
      setItem: () => {
        throw new Error("blocked");
      },
    };
    expect(readDetailsChoice(refusing, "user_1")).toBeNull();
    expect(() => writeDetailsChoice(refusing, "user_1", "closed")).not.toThrow();
    const odd = memory();
    odd.setItem("aw.technicalDetails:user_1", "maybe");
    expect(readDetailsChoice(odd, "user_1")).toBeNull();
  });
});
