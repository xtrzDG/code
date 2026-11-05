import { describe, expect, it } from "vitest";

import { accentRule } from "./accentRule";

describe("accentRule", () => {
  it("gives the page the accent and the text colour on it", () => {
    expect(accentRule("main.hc-page", { "--hc-accent": "#AD5732", "--hc-on-accent": "#ffffff" })).toBe(
      "main.hc-page{--hc-accent:#ad5732;--hc-on-accent:#ffffff}",
    );
  });

  it("lets only hex colours into the stylesheet", () => {
    expect(accentRule("main.hc-preview", { "--hc-accent": "#abc" })).toBe("main.hc-preview{--hc-accent:#abc}");
    expect(accentRule("main.hc-page", { "--hc-accent": "red;}body{display:none" })).toBeNull();
    expect(accentRule("main.hc-page", { "--hc-accent": "#12345</style><script>" })).toBeNull();
    expect(accentRule("main.hc-page", { "--hc-accent": null })).toBeNull();
    expect(accentRule("main.hc-page", {})).toBeNull();
  });
});
