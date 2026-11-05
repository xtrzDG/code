// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";

import { clearSessionStorage, signOut } from "./signOut";

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
  sessionStorage.clear();
});

describe("signing out", () => {
  it("ends the session and empties this site's Web Storage, the test chat included", async () => {
    const fetchMock = vi.fn(async () => new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);
    sessionStorage.setItem("aw:test-chat:business_1", '{"messages":[]}');
    localStorage.setItem("aw:tunnel-draft", "{}");

    await signOut();

    expect(fetchMock).toHaveBeenCalledWith("/api/auth/logout", { method: "POST" });
    expect(sessionStorage.length).toBe(0);
    expect(localStorage.length).toBe(0);
  });

  it("empties the storage even when the server is out of reach", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => Promise.reject(new Error("offline"))));
    sessionStorage.setItem("aw:test-chat:business_1", "{}");

    await expect(signOut()).resolves.toBeUndefined();
    expect(sessionStorage.length).toBe(0);
  });

  it("forgets an earlier session's test chat at the next sign-in", () => {
    sessionStorage.setItem("aw:test-chat:business_1", "{}");

    clearSessionStorage();

    expect(sessionStorage.length).toBe(0);
  });
});
