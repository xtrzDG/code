import { describe, expect, it } from "vitest";

import { parseInline, parseMarkdown } from "./markdown";

describe("parseInline", () => {
  it("marks bold parts and keeps unmatched markers as text", () => {
    expect(parseInline("by **default 90 days** of storage")).toEqual([
      { text: "by ", bold: false },
      { text: "default 90 days", bold: true },
      { text: " of storage", bold: false },
    ]);
    expect(parseInline("a ** b")).toEqual([
      { text: "a ", bold: false },
      { text: "** b", bold: false },
    ]);
  });
});

describe("parseMarkdown", () => {
  it("reads headings, paragraphs, lists, quotes and tables", () => {
    const blocks = parseMarkdown(
      [
        "# Agreement",
        "",
        "> **Template.** Have it",
        "> reviewed.",
        "",
        "## 1. Parties",
        "",
        "1.1. First line",
        "continues here.",
        "",
        "- one",
        "  more",
        "- two",
        "",
        "| A | B |",
        "| --- | --- |",
        "| x | **y** |",
      ].join("\n"),
    );

    expect(blocks.map((block) => block.kind)).toEqual(["heading", "quote", "heading", "paragraph", "list", "table"]);
    expect(blocks[0]).toEqual({ kind: "heading", level: 1, spans: [{ text: "Agreement", bold: false }] });
    expect(blocks[1]).toEqual({
      kind: "quote",
      paragraphs: [
        [
          { text: "Template.", bold: true },
          { text: " Have it reviewed.", bold: false },
        ],
      ],
    });
    expect(blocks[3]).toEqual({ kind: "paragraph", spans: [{ text: "1.1. First line continues here.", bold: false }] });
    expect(blocks[4]).toEqual({
      kind: "list",
      items: [[{ text: "one more", bold: false }], [{ text: "two", bold: false }]],
    });
    expect(blocks[5]).toEqual({
      kind: "table",
      header: [[{ text: "A", bold: false }], [{ text: "B", bold: false }]],
      rows: [[[{ text: "x", bold: false }], [{ text: "y", bold: true }]]],
    });
  });

  it("never turns markup into HTML", () => {
    const blocks = parseMarkdown("<script>alert(1)</script>");
    expect(blocks).toEqual([{ kind: "paragraph", spans: [{ text: "<script>alert(1)</script>", bold: false }] }]);
  });
});
