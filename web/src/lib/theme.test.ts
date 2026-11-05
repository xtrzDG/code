import { describe, expect, it } from "vitest";

import { DEFAULT_THEME, SCHEME_BACKGROUNDS, parseTheme, themeColors, themeCookie } from "./theme";

describe("theme", () => {
  it("reads the cookie and falls back to dark", () => {
    expect(parseTheme("light")).toBe("light");
    expect(parseTheme("system")).toBe("system");
    expect(parseTheme("dark")).toBe("dark");
    expect(parseTheme("sepia")).toBe(DEFAULT_THEME);
    expect(parseTheme(undefined)).toBe("dark");
  });

  it("gives the browser one colour per system scheme", () => {
    expect(themeColors("dark").map((entry) => entry.color)).toEqual([SCHEME_BACKGROUNDS.dark, SCHEME_BACKGROUNDS.dark]);
    expect(themeColors("light").map((entry) => entry.color)).toEqual([SCHEME_BACKGROUNDS.light, SCHEME_BACKGROUNDS.light]);
    expect(themeColors("system")).toEqual([
      { media: "(prefers-color-scheme: light)", color: SCHEME_BACKGROUNDS.light },
      { media: "(prefers-color-scheme: dark)", color: SCHEME_BACKGROUNDS.dark },
    ]);
  });

  it("stores the choice for a year on the whole site", () => {
    expect(themeCookie("light", false)).toBe("aw_theme=light; path=/; max-age=31536000; samesite=lax");
    expect(themeCookie("system", true)).toContain("; secure");
  });
});
