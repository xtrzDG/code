import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ConsentBannerSlot } from "./ConsentBannerSlot";

const cookieValues = new Map<string, string>();

vi.mock("next/headers", () => ({
  cookies: vi.fn(async () => ({
    get: (name: string) => (cookieValues.has(name) ? { name, value: cookieValues.get(name) } : undefined),
  })),
}));
vi.mock("@/i18n/server", async () => {
  const { textsIn } = await import("@/test/render");
  return { getI18n: vi.fn(async () => textsIn("it")) };
});

async function slotMarkup(): Promise<string> {
  return renderToStaticMarkup(await ConsentBannerSlot());
}

beforeEach(() => {
  cookieValues.clear();
});

describe("the cookie banner's slot", () => {
  it("opens the banner in the page's language for a visitor who has not answered, linking the statement", async () => {
    const markup = await slotMarkup();

    expect(markup).toContain('data-cookie-consent=""');
    expect(markup).toContain("Cookie su questo sito");
    expect(markup).toContain('href="/it/cookies"');
  });

  it("hides the box without scripts, where no answer can be given", async () => {
    const markup = await slotMarkup();

    expect(markup).toMatch(/<noscript><style[^>]*>\[data-cookie-consent\]\{display:none\}<\/style><\/noscript>/);
  });

  it("renders nothing for a visitor who answered the current question", async () => {
    for (const answer of ["1.granted", "1.denied"]) {
      cookieValues.set("aw_consent", answer);

      expect(await slotMarkup(), answer).toBe("");
    }
  });

  it("asks again after an answer to an older question", async () => {
    cookieValues.set("aw_consent", "0.granted");

    expect(await slotMarkup()).toContain("data-cookie-consent");
  });
});
