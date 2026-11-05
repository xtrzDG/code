import { describe, expect, it } from "vitest";

import { VIEWER_TIME_ZONE_COOKIE, parseViewerTimeZone, viewerTimeZoneCookie } from "./viewerTimeZone";

describe("the reader's time zone cookie", () => {
  it("round-trips a zone through the cookie value", () => {
    const cookie = viewerTimeZoneCookie("America/Argentina/Buenos_Aires", false);
    expect(cookie).toBe(`${VIEWER_TIME_ZONE_COOKIE}=America%2FArgentina%2FBuenos_Aires; path=/; max-age=31536000; samesite=lax`);
    const value = cookie.split(";")[0]!.split("=")[1];
    expect(parseViewerTimeZone(value)).toBe("America/Argentina/Buenos_Aires");
  });

  it("marks the cookie secure on https", () => {
    expect(viewerTimeZoneCookie("Asia/Tbilisi", true).endsWith("; secure")).toBe(true);
  });

  it("reads plain and encoded zones, and ignores anything else", () => {
    expect(parseViewerTimeZone("Asia/Tbilisi")).toBe("Asia/Tbilisi");
    expect(parseViewerTimeZone("Etc%2FGMT%2B5")).toBe("Etc/GMT+5");
    expect(parseViewerTimeZone(undefined)).toBeNull();
    expect(parseViewerTimeZone(null)).toBeNull();
    expect(parseViewerTimeZone("")).toBeNull();
    expect(parseViewerTimeZone("Mars/Base")).toBeNull();
    expect(parseViewerTimeZone("Asia/Tbilisi<script>")).toBeNull();
    expect(parseViewerTimeZone("%E0%A4%A")).toBeNull();
  });
});
