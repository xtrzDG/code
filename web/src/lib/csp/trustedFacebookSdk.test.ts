import { afterEach, describe, expect, it, vi } from "vitest";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.resetModules();
});

type ScriptUrlRules = { createScriptURL: (value: string) => string };

function stubTrustedTypes() {
  const createPolicy = vi.fn((_name: string, rules: ScriptUrlRules) => ({
    createScriptURL: (value: string) => ({ trusted: rules.createScriptURL(value) }),
  }));
  vi.stubGlobal("trustedTypes", { createPolicy });
  return createPolicy;
}

describe("trustedFacebookSdkUrl", () => {
  it("vouches for the SDK's own address through one named policy", async () => {
    const createPolicy = stubTrustedTypes();
    const { trustedFacebookSdkUrl } = await import("./trustedFacebookSdk");

    expect(trustedFacebookSdkUrl("https://connect.facebook.net/ka_GE/sdk.js")).toEqual({
      trusted: "https://connect.facebook.net/ka_GE/sdk.js",
    });
    trustedFacebookSdkUrl("https://connect.facebook.net/en_US/sdk.js");
    expect(createPolicy).toHaveBeenCalledTimes(1);
    expect(createPolicy.mock.calls[0]?.[0]).toBe("facebook-sdk");
  });

  it("refuses every other address, Facebook's own included", async () => {
    stubTrustedTypes();
    const { trustedFacebookSdkUrl } = await import("./trustedFacebookSdk");

    for (const address of [
      "https://connect.facebook.net/en_US/fbevents.js",
      "https://connect.facebook.net/en_US/sdk.js?debug=1",
      "https://connect.facebook.net.example.com/en_US/sdk.js",
      "http://connect.facebook.net/en_US/sdk.js",
      "/_next/static/chunks/app.js",
    ]) {
      expect(() => trustedFacebookSdkUrl(address), address).toThrow(TypeError);
    }
  });

  it("is the string itself without Trusted Types", async () => {
    vi.stubGlobal("trustedTypes", undefined);
    const { trustedFacebookSdkUrl } = await import("./trustedFacebookSdk");

    expect(trustedFacebookSdkUrl("https://connect.facebook.net/en_US/sdk.js")).toBe(
      "https://connect.facebook.net/en_US/sdk.js",
    );
  });
});
