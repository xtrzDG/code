import { describe, expect, it } from "vitest";

import { installModeOf, isAppleMobile } from "./installPrompt";

const IPHONE = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Version/18.0 Mobile/15E148 Safari/604.1";
const IPAD_DESKTOP = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/18.0 Safari/605.1.15";
const ANDROID = "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 Chrome/141.0 Mobile Safari/537.36";

describe("installing the cabinet as an app", () => {
  it("recognises iPhones and iPads (which say Macintosh but have touch)", () => {
    expect(isAppleMobile(IPHONE, 5)).toBe(true);
    expect(isAppleMobile(IPAD_DESKTOP, 5)).toBe(true);
    expect(isAppleMobile(IPAD_DESKTOP, 0)).toBe(false);
    expect(isAppleMobile(ANDROID, 5)).toBe(false);
  });

  it("offers the browser's prompt, the iOS steps, or nothing", () => {
    const base = { isStandalone: false, hasPrompt: false, userAgent: ANDROID, maxTouchPoints: 5 };
    expect(installModeOf({ ...base, hasPrompt: true })).toBe("prompt");
    expect(installModeOf({ ...base, userAgent: IPHONE })).toBe("ios");
    expect(installModeOf(base)).toBe("unavailable");
    expect(installModeOf({ ...base, isStandalone: true, hasPrompt: true })).toBe("installed");
  });
});
