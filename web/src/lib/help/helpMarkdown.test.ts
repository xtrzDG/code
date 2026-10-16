import { describe, expect, it } from "vitest";

import { articleLinks, linkTarget, parseHelpInline, parseHelpMarkdown } from "./helpMarkdown";

const plain = (text: string) => ({ text, bold: false, code: false, link: null });

describe("parseHelpInline", () => {
  it("reads bold, code and plain text", () => {
    expect(parseHelpInline("Send `/newbot` to **BotFather** now")).toEqual([
      plain("Send "),
      { text: "/newbot", bold: false, code: true, link: null },
      plain(" to "),
      { text: "BotFather", bold: true, code: false, link: null },
      plain(" now"),
    ]);
  });

  it("keeps an unmatched ** or ` as text", () => {
    expect(parseHelpInline("2 ** 3 and a ` tick")).toEqual([plain("2 ** 3 and a ` tick")]);
  });

  it("reads links to articles, cabinet pages and https addresses", () => {
    expect(parseHelpInline("See [Inbox](inbox), [Channels](cabinet:assistant/channels) or [Meta](https://meta.com/x).")).toEqual([
      plain("See "),
      { text: "Inbox", bold: false, code: false, link: { kind: "article", slug: "inbox" } },
      plain(", "),
      { text: "Channels", bold: false, code: false, link: { kind: "cabinet", page: "assistant/channels" } },
      plain(" or "),
      { text: "Meta", bold: false, code: false, link: { kind: "external", href: "https://meta.com/x" } },
      plain("."),
    ]);
  });

  it("keeps a link bold inside bold text", () => {
    expect(parseHelpInline("**Settings → [Calls](cabinet:settings/calls)**")).toEqual([
      { text: "Settings → ", bold: true, code: false, link: null },
      { text: "Calls", bold: true, code: false, link: { kind: "cabinet", page: "settings/calls" } },
    ]);
  });

  it("leaves a link of an unknown kind as text", () => {
    expect(parseHelpInline("[x](javascript:alert)")).toEqual([{ text: "x", bold: false, code: false, link: null }]);
  });
});

describe("linkTarget", () => {
  it("refuses what is not an article, a cabinet page or https", () => {
    expect(linkTarget("http://example.com")).toBeNull();
    expect(linkTarget("cabinet:nowhere")).toBeNull();
    expect(linkTarget("Not_A_Slug")).toBeNull();
    expect(linkTarget("billing")).toEqual({ kind: "article", slug: "billing" });
  });
});

describe("parseHelpMarkdown", () => {
  it("reads headings, paragraphs, lists, tips and tables", () => {
    const source = [
      "Intro line one",
      "continues here.",
      "",
      "## Connect",
      "### Details ##",
      "1. First",
      "   still first",
      "2) Second",
      "- Bullet",
      "* Star",
      "",
      "> A tip",
      "> on two lines",
      "",
      "| Operator | Code |",
      "| --- | --- |",
      "| Magti | `*21*` |",
    ].join("\r\n");

    expect(parseHelpMarkdown(source)).toEqual([
      { kind: "paragraph", spans: [plain("Intro line one continues here.")] },
      { kind: "heading", level: 2, spans: [plain("Connect")] },
      { kind: "heading", level: 3, spans: [plain("Details")] },
      { kind: "list", ordered: true, items: [[plain("First still first")], [plain("Second")]] },
      { kind: "list", ordered: false, items: [[plain("Bullet")], [plain("Star")]] },
      { kind: "tip", spans: [plain("A tip on two lines")] },
      {
        kind: "table",
        header: [[plain("Operator")], [plain("Code")]],
        rows: [[[plain("Magti")], [{ text: "*21*", bold: false, code: true, link: null }]]],
      },
    ]);
  });

  it("ends a paragraph where a list starts", () => {
    expect(parseHelpMarkdown("Text\n- item").map((block) => block.kind)).toEqual(["paragraph", "list"]);
  });

  it("treats a line starting with | without a separator as text", () => {
    expect(parseHelpMarkdown("| not a table")).toEqual([{ kind: "paragraph", spans: [plain("| not a table")] }]);
  });
});

describe("articleLinks", () => {
  it("lists every link target", () => {
    expect(articleLinks("[a](inbox) and [b](cabinet:bookings)")).toEqual(["inbox", "cabinet:bookings"]);
  });
});
