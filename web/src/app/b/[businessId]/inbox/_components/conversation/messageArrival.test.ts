import { describe, expect, it } from "vitest";

import { arrivalMotion, isArrival, openingMessages } from "./messageArrival";

const OPENED = [
  { id: "m1", created_at: 100 },
  { id: "m2", created_at: 300 },
  { id: "m3", created_at: 200 },
];

describe("a message arriving in an open conversation", () => {
  it("remembers the messages the transcript opened with and the newest moment among them", () => {
    const opening = openingMessages(OPENED);
    expect([...opening.ids]).toEqual(["m1", "m2", "m3"]);
    expect(opening.newestAt).toBe(300);
    expect(openingMessages([]).newestAt).toBe(Number.NEGATIVE_INFINITY);
  });

  it("counts only a new message after the newest one as an arrival", () => {
    const opening = openingMessages(OPENED);
    expect(isArrival({ id: "m4", created_at: 400 }, opening)).toBe(true);
    expect(isArrival({ id: "m2", created_at: 300 }, opening)).toBe(false);
    // An earlier message loaded on request is new on screen but did not just arrive.
    expect(isArrival({ id: "m0", created_at: 50 }, opening)).toBe(false);
    expect(isArrival({ id: "first", created_at: 1 }, openingMessages([]))).toBe(true);
  });

  it("springs in from below unless the person asked for calm, and never for the others", () => {
    expect(arrivalMotion(true, false).initial).toEqual({ opacity: 0, y: 14, scale: 0.96 });
    expect(arrivalMotion(true, false).transition).toMatchObject({ type: "spring" });
    expect(arrivalMotion(true, true).initial).toBe(false);
    expect(arrivalMotion(false, false).initial).toBe(false);
    expect(arrivalMotion(false, false).animate).toEqual({ opacity: 1, y: 0, scale: 1 });
  });
});
