import { describe, expect, it } from "vitest";

import { nextPresenceKey, rowMotion } from "./rowMotion";

describe("how an inbox row moves", () => {
  it("slides in, fades out and glides into place while live", () => {
    const motion = rowMotion(false);
    expect(motion.initial).toMatchObject({ opacity: 0, y: -10 });
    expect(motion.animate).toEqual({ opacity: 1, y: 0, scale: 1 });
    expect(motion.exit).toMatchObject({ opacity: 0 });
    expect(motion.layout).toBe("position");
  });

  it("neither enters, leaves nor glides when the person asked for calm", () => {
    const motion = rowMotion(true);
    expect(motion.initial).toBe(false);
    expect(motion.exit).toBeUndefined();
    expect(motion.layout).toBe(false);
    expect(motion.animate).toEqual({ opacity: 1, y: 0, scale: 1 });
  });
});

describe("which list the rows belong to", () => {
  it("keeps the old key while another view loads, and takes the new one when its rows arrive", () => {
    expect(nextPresenceKey("view=all", "view=mine", true)).toBe("view=all");
    expect(nextPresenceKey("view=all", "view=mine", false)).toBe("view=mine");
    expect(nextPresenceKey("view=all", "view=all", false)).toBe("view=all");
  });
});
