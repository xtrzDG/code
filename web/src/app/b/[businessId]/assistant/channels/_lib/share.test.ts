import { describe, expect, it } from "vitest";

import { encodeQr } from "./qrCode";
import {
  displayUrl,
  downloadName,
  isShareSource,
  isValidSlug,
  normalizeSlugInput,
  SHARE_SOURCES,
  SOURCE_LABELS,
  usableLinks,
  type ShareLinks,
} from "./share";
import { buildTableCardHtml, printFrame } from "./tableCard";

const VIEW: ShareLinks = {
  business_id: "business_1",
  slug: "cafe-batumi",
  hosted_chat_url: "https://app.example/c/cafe-batumi",
  links: [
    { kind: "hosted_chat", url: "https://app.example/c/cafe-batumi", label: "app.example/c/cafe-batumi" },
    { kind: "whatsapp", url: null, gap: "reconnect_channel" },
    { kind: "phone", url: "tel:+995322190019", label: "+995322190019" },
  ],
};

describe("share links", () => {
  it("names every tag and accepts only known ones", () => {
    expect(Object.keys(SOURCE_LABELS).sort()).toEqual([...SHARE_SOURCES].sort());
    expect(isShareSource("table")).toBe(true);
    expect(isShareSource("tiktok")).toBe(false);
  });

  it("shows links without the scheme and keeps only those that work", () => {
    expect(displayUrl("https://t.me/cafe_bot")).toBe("t.me/cafe_bot");
    expect(displayUrl("tel:+995322190019")).toBe("+995322190019");
    expect(usableLinks(VIEW).map((link) => link.kind)).toEqual(["hosted_chat", "phone"]);
    expect(usableLinks(undefined)).toEqual([]);
  });

  it("names downloads after the address, channel and tag", () => {
    expect(downloadName("cafe-batumi", "hosted_chat", "")).toBe("chat-cafe-batumi");
    expect(downloadName("cafe-batumi", "whatsapp", "table")).toBe("chat-cafe-batumi-whatsapp-table");
    expect(downloadName("cafe", "hosted_chat", "flyer")).toBe("chat-cafe-flyer");
  });

  it("writes an address the way the API accepts it", () => {
    expect(normalizeSlugInput("Cafe Batumi_2!")).toBe("cafe-batumi-2");
    expect(normalizeSlugInput("x".repeat(60))).toHaveLength(40);
    expect(isValidSlug("cafe-batumi")).toBe(true);
    expect(isValidSlug("ab")).toBe(false);
    expect(isValidSlug("-cafe")).toBe(false);
    expect(isValidSlug("cafe--batumi")).toBe(false);
    expect(isValidSlug("cafe-")).toBe(false);
  });
});

describe("the table card", () => {
  const card = {
    businessName: `Café <b>"Ezo"</b>`,
    linkText: "app.example/c/cafe?src=table",
    matrix: encodeQr("https://app.example/c/cafe?src=table"),
    language: "he",
    direction: "rtl" as const,
    accent: "#2F7D4F",
    heading: "סרקו כדי לכתוב לנו",
    hint: "שאלו אותנו כל דבר",
  };

  it("is an A6 page in the customers' language with everything escaped", () => {
    const html = buildTableCardHtml(card);

    expect(html).toContain("@page { size: 105mm 148mm; margin: 0; }");
    expect(html).toContain('<html lang="he" dir="rtl">');
    expect(html).toContain("Café &lt;b&gt;&quot;Ezo&quot;&lt;/b&gt;");
    expect(html).not.toContain("<b>");
    expect(html).toContain("--accent: #2F7D4F");
    expect(html).toContain("סרקו כדי לכתוב לנו");
    expect(html).toContain('<p class="link">app.example/c/cafe?src=table</p>');
    expect(html).not.toContain("<script");
  });

  it("falls back to the cabinet's accent for a colour that is not #rrggbb", () => {
    expect(buildTableCardHtml({ ...card, accent: "red;}" })).toContain("--accent: #5b5bd6");
    expect(buildTableCardHtml({ ...card, accent: null })).toContain("--accent: #5b5bd6");
  });

  it("prints the frame's document, and says when it cannot", () => {
    const print = () => undefined;
    const frame = { contentWindow: { focus: () => undefined, print } } as unknown as HTMLIFrameElement;
    const blocked = {
      contentWindow: {
        focus: () => undefined,
        print: () => {
          throw new Error("blocked");
        },
      },
    } as unknown as HTMLIFrameElement;

    expect(printFrame(frame)).toBe(true);
    expect(printFrame(blocked)).toBe(false);
    expect(printFrame(null)).toBe(false);
  });
});
