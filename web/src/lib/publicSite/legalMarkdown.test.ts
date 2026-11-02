import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

import { parseMarkdown, type InlineSpan } from "@/components/workspace/markdown";

/**
 * Every published legal text (the files docs/legal/published.json records
 * and every other text the API serves from docs/legal: the terms, the
 * privacy policy, the cookie statement, the security page and the DPA, as
 * the API serves them) uses only the Markdown the public pages render
 * (components/workspace/markdown.ts): headings #, ## and ###, paragraphs,
 * "- " lists, "> " quotes, tables and **bold**. Anything else would show
 * as raw characters (a link's brackets, a backtick, a fourth #) or run two
 * clauses into one paragraph. A published text never changes, so a problem
 * found here goes into the next dated version.
 */

const LEGAL_DIRECTORY = path.resolve(__dirname, "..", "..", "..", "..", "docs", "legal");

/** A text the API serves (GET /v1/legal/…): docs/legal/<kind>-<date>.<language>.md, drafts aside. */
const SERVED_TEXT = /^(terms|privacy|cookies|security|dpa)-\d{4}-\d{2}-\d{2}\.[a-z]{2}\.md$/;

function publishedTexts(): [string, string][] {
  const manifest = JSON.parse(readFileSync(path.join(LEGAL_DIRECTORY, "published.json"), "utf8")) as Record<string, string>;
  const served = readdirSync(LEGAL_DIRECTORY).filter((name) => SERVED_TEXT.test(name));
  return [...new Set([...Object.keys(manifest), ...served])]
    .sort()
    .map((name) => [name, readFileSync(path.join(LEGAL_DIRECTORY, name), "utf8")]);
}

/**
 * The text as the API serves it: the generated sub-processor table and
 * security measures without their HTML comment markers (the table itself
 * is rendered from the registry in the same shape).
 */
function asServed(source: string): string {
  return source.replace(/^<!-- (subprocessors|security-measures):(start|end)[^\n]*-->$/gm, "");
}

/** Syntax the renderer does not know, by the line it starts or appears on. */
const UNSUPPORTED_LINES: readonly [string, RegExp][] = [
  ["a heading deeper than ###", /^\s*#{4,}/],
  ["a link or an image", /!?\[[^\]]*\]\([^)]*\)/],
  ["inline code", /`/],
  ["HTML", /<\/?[A-Za-z!][^>]*>/],
  ["a list item with * or +", /^\s*[*+]\s/],
  ["a nested list item", /^\s{2,}-\s/],
  ["a numbered list item", /^\s*\d+[.)]\s/],
  ["a horizontal rule", /^\s*(-{3,}|\*{3,}|_{3,})\s*$/],
  ["*emphasis* (only **bold** is rendered)", /(^|[^*\\])\*(?!\*)[^*\s][^*]*(?<!\*)\*(?!\*)/],
];

/** Lines that are table rows or table separators. */
const TABLE_LINE = /^\s*\|/;

function spansText(spans: readonly InlineSpan[]): string {
  return spans.map((span) => span.text).join("");
}

function problemsOf(source: string): string[] {
  const text = asServed(source);
  const problems: string[] = [];
  const lines = text.split("\n");
  lines.forEach((line, index) => {
    for (const [what, pattern] of UNSUPPORTED_LINES) {
      if (pattern.test(line)) {
        problems.push(`line ${index + 1}: ${what}: ${line.trim()}`);
      }
    }
    // "1.2. …" right under another line would join that line's paragraph.
    const previous = lines[index - 1] ?? "";
    if (/^\d+(\.\d+)+\.?\s/.test(line) && previous.trim() !== "" && !TABLE_LINE.test(previous)) {
      problems.push(`line ${index + 1}: a numbered clause without a blank line before it: ${line.trim()}`);
    }
  });
  for (const block of parseMarkdown(text)) {
    const spans =
      block.kind === "heading" || block.kind === "paragraph"
        ? [block.spans]
        : block.kind === "list"
          ? block.items
          : block.kind === "quote"
            ? block.paragraphs
            : [...block.header, ...block.rows.flat()];
    for (const span of spans) {
      if (spansText(span).includes("**")) {
        problems.push(`an unmatched **: ${spansText(span)}`);
      }
    }
    if (block.kind === "table") {
      block.rows.forEach((row, index) => {
        if (row.length !== block.header.length) {
          problems.push(`table row ${index + 1} has ${row.length} cells, its header ${block.header.length}`);
        }
      });
    }
  }
  return problems;
}

describe("the published legal texts", () => {
  const texts = publishedTexts();

  it("are read from the published record", () => {
    expect(texts.map(([name]) => name.split("-")[0])).toEqual(expect.arrayContaining(["cookies", "dpa", "privacy", "security", "terms"]));
  });

  it.each(texts)("%s uses only the Markdown the site renders", (_name, source) => {
    expect(problemsOf(source)).toEqual([]);
  });

  it("catches what the renderer would show raw", () => {
    const bad = [
      "# Title",
      "",
      "See [the terms](https://example.com) and `code`.",
      "",
      "#### Deep",
      "",
      "* star item",
      "",
      "1. first",
      "1.1. clause",
      "",
      "A *note* and an **open bold.",
      "",
      "| A | B |",
      "| --- | --- |",
      "| only one |",
      "",
      "<b>html</b>",
      "",
      "---",
    ].join("\n");

    const problems = problemsOf(bad);

    for (const what of ["a link", "inline code", "deeper than ###", "* or +", "numbered list item", "numbered clause", "*emphasis*", "unmatched **", "table row 1", "HTML", "horizontal rule"]) {
      expect(problems.some((problem) => problem.includes(what)), what).toBe(true);
    }
    expect(problemsOf("# Title\n\nPlain **bold** text, __Host-aw_session and 1.1. inline.\n\n- an item\n  continued")).toEqual([]);
  });
});
