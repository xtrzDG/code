import { describe, expect, it } from "vitest";

import {
  basisPointsToPercent,
  isPayoutMonth,
  isSourceTag,
  linkWithSource,
  percentToBasisPoints,
  previousMonth,
  printableLink,
  shareMessage,
  utcMonth,
  withPoweredByFooter,
} from "./referralLinks";

const LINK = "https://app.example/?ref=agency-tbilisi&src=partner";

describe("partner links", () => {
  it("set the place a link is shared in as its src", () => {
    expect(linkWithSource(LINK, "instagram")).toBe("https://app.example/?ref=agency-tbilisi&src=instagram");
    expect(linkWithSource(LINK, "  ")).toBe(LINK);
    expect(linkWithSource(LINK, "no spaces")).toBe(LINK);
    expect(linkWithSource("not a link", "qr")).toBe("not a link");
  });

  it("take only the tags the API accepts", () => {
    expect(isSourceTag("fb.story_2")).toBe(true);
    expect(isSourceTag("<script>")).toBe(false);
    expect(isSourceTag("x".repeat(65))).toBe(false);
  });

  it("put the invitation before the link", () => {
    expect(shareMessage("Sign up:", LINK)).toBe(`Sign up: ${LINK}`);
  });
});

describe("rates and months", () => {
  it("turn basis points into percents and back", () => {
    expect(basisPointsToPercent(2000)).toBe(20);
    expect(basisPointsToPercent(1250)).toBe(12.5);
    expect(percentToBasisPoints("12,5")).toBe(1250);
    expect(percentToBasisPoints("20")).toBe(2000);
    expect(percentToBasisPoints("51")).toBeNull();
    expect(percentToBasisPoints("-1")).toBeNull();
    expect(percentToBasisPoints("ten")).toBeNull();
  });

  it("name payout months in UTC", () => {
    expect(utcMonth(new Date("2026-10-31T23:30:00-02:00"))).toBe("2026-11");
    expect(previousMonth("2026-01")).toBe("2025-12");
    expect(previousMonth("2026-10")).toBe("2026-09");
    expect(isPayoutMonth("2026-10")).toBe(true);
    expect(isPayoutMonth("2026-13")).toBe(false);
  });
});

describe("the table card's Powered by line", () => {
  const card = '<html><body><main class="card"><p class="link">x</p></main></body></html>';

  it("goes at the card's foot, escaped, without the scheme", () => {
    const html = withPoweredByFooter(card, "Powered by <Workshop>", LINK);

    expect(html).toContain("Powered by &lt;Workshop&gt; · app.example/?ref=agency-tbilisi&amp;src=partner</p></main>");
    expect(printableLink(LINK)).toBe("app.example/?ref=agency-tbilisi&src=partner");
  });

  it("is left out without a link", () => {
    expect(withPoweredByFooter(card, "Powered by", null)).toBe(card);
    expect(withPoweredByFooter("<p>no main</p>", "Powered by", LINK)).toBe("<p>no main</p>");
  });
});

describe("the Powered by line's language", () => {
  it("follows the base language and falls back to English", async () => {
    const { poweredByText } = await import("./poweredByTexts");

    expect(poweredByText("ka")).toBe("მუშაობს Assistant Workshop-ზე");
    expect(poweredByText("pt-BR")).toBe("Desenvolvido com Assistant Workshop");
    expect(poweredByText("sw")).toBe("Powered by Assistant Workshop");
  });
});
