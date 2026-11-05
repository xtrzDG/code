import { afterEach, describe, expect, it, vi } from "vitest";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.resetModules();
});

describe("trustedOwnMarkup", () => {
  it("vouches for the cabinet's own markup through one named policy", async () => {
    const createPolicy = vi.fn((_name: string, rules: { createHTML: (value: string) => string }) => ({
      createHTML: (value: string) => ({ trusted: rules.createHTML(value) }),
    }));
    vi.stubGlobal("trustedTypes", { createPolicy });
    const { trustedOwnMarkup } = await import("./trustedMarkup");

    expect(trustedOwnMarkup("<p>card</p>")).toEqual({ trusted: "<p>card</p>" });
    trustedOwnMarkup("<p>again</p>");
    expect(createPolicy).toHaveBeenCalledTimes(1);
    expect(createPolicy.mock.calls[0]?.[0]).toBe("cabinet-markup");
  });

  it("is the string itself without Trusted Types", async () => {
    vi.stubGlobal("trustedTypes", undefined);
    const { trustedOwnMarkup } = await import("./trustedMarkup");

    expect(trustedOwnMarkup("<p>card</p>")).toBe("<p>card</p>");
  });
});
