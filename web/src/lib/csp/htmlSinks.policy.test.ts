/**
 * Untrusted text (customers' messages and names, call transcripts, model
 * replies, knowledge texts) reaches the page only as text (INP-02): React
 * escapes it. Markup goes to the browser only from the files reviewed for
 * it (REVIEWED_HTML_SINK_FILES in eslint.config.mjs), each of which builds
 * it from constant or escaped parts; ESLint refuses a raw HTML sink
 * anywhere else, and this test keeps the list and the code in step.
 */

import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";

import { ESLint } from "eslint";
import { describe, expect, it } from "vitest";

const WEB_DIRECTORY = path.resolve(__dirname, "../../..");
const SOURCE_DIRECTORY = path.join(WEB_DIRECTORY, "src");

/** The reviewed files and what each one hands to the browser. */
const REVIEWED: Record<string, string> = {
  "src/components/csp/TrustedTypesScript.tsx": "a constant bootstrap script",
  "src/app/_landing/JsonLd.tsx": "JSON-LD serialized with every < escaped",
  "src/app/c/[slug]/page.tsx": "an empty container the widget fills",
  "src/app/b/[businessId]/assistant/channels/_components/TableCardPanel.tsx": "the table card, built from escaped parts",
};

const HTML_SINK = /dangerouslySetInnerHTML|srcDoc=|\.(innerHTML|outerHTML)\s*=|insertAdjacentHTML|document\.write/;

function sourceFiles(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const full = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      return entry.name === "test" && directory === SOURCE_DIRECTORY ? [] : sourceFiles(full);
    }
    return /\.(ts|tsx|mts)$/.test(entry.name) && !entry.name.includes(".test.") ? [full] : [];
  });
}

const PROBE = [
  "export function Unsafe({ text }: { text: string }) {",
  "  return <div dangerouslySetInnerHTML={{ __html: text }} />;",
  "}",
  "export function alsoUnsafe(element: HTMLElement, text: string) {",
  "  element.innerHTML = text;",
  "}",
  "",
].join("\n");

async function ruleIds(filePath: string): Promise<string[]> {
  const eslint = new ESLint({ cwd: WEB_DIRECTORY });
  const results = await eslint.lintText(PROBE, { filePath: path.join(WEB_DIRECTORY, filePath) });
  return results.flatMap((result) => result.messages.map((message) => message.ruleId ?? ""));
}

describe("raw HTML sinks", () => {
  it("appear only in the reviewed files", () => {
    const withSinks = sourceFiles(SOURCE_DIRECTORY)
      .filter((file) => HTML_SINK.test(readFileSync(file, "utf8")))
      .map((file) => path.relative(WEB_DIRECTORY, file).split(path.sep).join("/"))
      .sort();

    expect(withSinks).toEqual(Object.keys(REVIEWED).sort());
  });

  it("are refused by ESLint anywhere else", async () => {
    const ids = await ruleIds("src/components/conversation/Probe.tsx");

    expect(ids).toContain("react/no-danger");
    expect(ids).toContain("no-restricted-properties");
  }, 60_000);

  it("are allowed by ESLint in each reviewed file", async () => {
    for (const file of Object.keys(REVIEWED)) {
      const ids = await ruleIds(file);
      expect(ids.filter((id) => id === "react/no-danger" || id === "no-restricted-properties"), file).toEqual([]);
    }
  }, 60_000);
});
