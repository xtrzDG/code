import { afterEach, describe, expect, it, vi } from "vitest";

import {
  DEFAULT_MOTION_PREFERENCE,
  MOTION_ATTRIBUTE,
  isCalm,
  motionAttribute,
  motionCookie,
  parseMotionPreference,
  prefersCalmMotion,
} from "./motionPreference";

describe("the motion preference", () => {
  it("reads the cookie and follows the device for anything else", () => {
    expect(parseMotionPreference("reduce")).toBe("reduce");
    expect(parseMotionPreference("system")).toBe("system");
    expect(parseMotionPreference("full")).toBe(DEFAULT_MOTION_PREFERENCE);
    expect(parseMotionPreference(undefined)).toBe("system");
    expect(parseMotionPreference(null)).toBe("system");
  });

  it("stores the choice for a year on the whole site", () => {
    expect(motionCookie("reduce", false)).toBe("aw_motion=reduce; path=/; max-age=31536000; samesite=lax");
    expect(motionCookie("system", true)).toBe("aw_motion=system; path=/; max-age=31536000; samesite=lax; secure");
  });

  it("marks <html> only when the person asked for less motion", () => {
    expect(motionAttribute("reduce")).toBe("reduce");
    expect(motionAttribute("system")).toBeUndefined();
  });

  it("is calm when either the person or the device asks for it, never less", () => {
    expect(isCalm("system", false)).toBe(false);
    expect(isCalm("system", true)).toBe(true);
    expect(isCalm("reduce", false)).toBe(true);
    expect(isCalm("reduce", true)).toBe(true);
  });
});

describe("prefersCalmMotion (outside React)", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("is false on the server", () => {
    expect(prefersCalmMotion()).toBe(false);
  });

  function stubBrowser({ attribute, deviceReduces }: { attribute: string | null; deviceReduces: boolean }) {
    vi.stubGlobal("window", { matchMedia: (query: string) => ({ matches: deviceReduces && query.includes("reduce") }) });
    vi.stubGlobal("document", {
      documentElement: { getAttribute: (name: string) => (name === MOTION_ATTRIBUTE ? attribute : null) },
    });
  }

  it("reads the page's attribute and the device's setting", () => {
    stubBrowser({ attribute: null, deviceReduces: false });
    expect(prefersCalmMotion()).toBe(false);
    stubBrowser({ attribute: "reduce", deviceReduces: false });
    expect(prefersCalmMotion()).toBe(true);
    stubBrowser({ attribute: null, deviceReduces: true });
    expect(prefersCalmMotion()).toBe(true);
  });
});
