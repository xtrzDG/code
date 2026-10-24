import { afterEach, describe, expect, it, vi } from "vitest";

import { countryName } from "./countries";
import { languageName } from "./format";

/** A browser without display names for the locale (Chrome and Georgian): Intl echoes the code. */
class CodeEchoingDisplayNames {
  of(code: string): string {
    return code;
  }
}

describe("names in the interface languages", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("come from the CLDR table, not from the browser's Intl data", () => {
    vi.stubGlobal("Intl", { ...Intl, DisplayNames: CodeEchoingDisplayNames });

    expect(countryName("GE", "ka")).toBe("საქართველო");
    expect(countryName("de", "ka")).toBe("გერმანია");
    expect(countryName("GE", "ru")).toBe("Грузия");
    expect(languageName("ru", "ka")).toBe("რუსული");
    expect(languageName("ka", "ru")).toBe("Грузинский");
    expect(languageName("he", "en")).toBe("Hebrew");
  });

  it("fall back to Intl for other interface languages and unknown codes", () => {
    expect(countryName("GE", "de")).toBe("Georgien");
    expect(languageName("pt-BR", "en")).toBe("Brazilian Portuguese");
    expect(countryName("ZZZ", "en")).toBe("ZZZ");
  });
});
