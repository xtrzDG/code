// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type * as FacebookSdkModule from "./facebookSdk";
import type { FacebookSdk } from "./facebookSdk";

// The loader keeps its one load per page: each test gets a fresh module.
let sdkModule: typeof FacebookSdkModule;
beforeEach(async () => {
  vi.resetModules();
  sdkModule = await import("./facebookSdk");
});
const loadFacebookSdk = (locale: string) => sdkModule.loadFacebookSdk(locale);
const facebookSdkUrl = (locale: string) => sdkModule.facebookSdkUrl(locale);

const SDK: FacebookSdk = { init: vi.fn(), login: vi.fn() };

function sdkScripts(): HTMLScriptElement[] {
  return [...document.querySelectorAll<HTMLScriptElement>("script[src*='connect.facebook.net']")];
}

afterEach(() => {
  vi.useRealTimers();
  delete window.FB;
  delete window.fbAsyncInit;
  for (const script of sdkScripts()) {
    script.remove();
  }
});

describe("Facebook's SDK", () => {
  it("comes from Facebook in the cabinet's language", () => {
    expect(facebookSdkUrl("ka")).toBe("https://connect.facebook.net/ka_GE/sdk.js");
    expect(facebookSdkUrl("he")).toBe("https://connect.facebook.net/he_IL/sdk.js");
    expect(facebookSdkUrl("xx")).toBe("https://connect.facebook.net/en_US/sdk.js");
  });

  it("loads once, when first asked for, and is ready when it says so", async () => {
    const first = loadFacebookSdk("ru");
    const second = loadFacebookSdk("ru");

    expect(sdkScripts().map((script) => script.src)).toEqual(["https://connect.facebook.net/ru_RU/sdk.js"]);
    expect(sdkScripts()[0]?.crossOrigin).toBe("anonymous");
    window.FB = SDK;
    window.fbAsyncInit?.();

    await expect(first).resolves.toBe(SDK);
    await expect(second).resolves.toBe(SDK);
    await expect(loadFacebookSdk("ru")).resolves.toBe(SDK);
  });

  it("can be tried again after it failed to load", async () => {
    const failed = loadFacebookSdk("en");
    sdkScripts()[0]?.dispatchEvent(new Event("error"));

    await expect(failed).rejects.toThrow("did not load");
    expect(sdkScripts()).toEqual([]);

    const again = loadFacebookSdk("en");
    window.FB = SDK;
    sdkScripts()[0]?.dispatchEvent(new Event("load"));
    await expect(again).resolves.toBe(SDK);
  });

  it("gives up when it never answers", async () => {
    vi.useFakeTimers();
    const hanging = loadFacebookSdk("de");
    // Loaded, but without the SDK: still waiting for it.
    sdkScripts()[0]?.dispatchEvent(new Event("load"));

    vi.advanceTimersByTime(20_000);

    await expect(hanging).rejects.toThrow("did not load");
  });
});
