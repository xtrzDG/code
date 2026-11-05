/**
 * The help articles' Markdown (docs/help/README.md) as plain data: `##` and
 * `###` headings, paragraphs, bullet and numbered lists, tables, `> ` tips,
 * and inline **bold**, `code` and links. React renders the result as text,
 * so nothing in an article can inject HTML; a link is one of three kinds
 * (another article, a page of the cabinet, an https address), anything else
 * stays text.
 */

import type { BusinessPage } from "@/lib/navigation";

import { cabinetPage } from "./helpTopics";

export type HelpLinkTarget =
  | { kind: "article"; slug: string }
  | { kind: "cabinet"; page: BusinessPage }
  | { kind: "external"; href: string };

export interface HelpSpan {
  text: string;
  bold: boolean;
  code: boolean;
  link: HelpLinkTarget | null;
}

export type HelpBlock =
  | { kind: "heading"; level: 2 | 3; spans: HelpSpan[] }
  | { kind: "paragraph"; spans: HelpSpan[] }
  | { kind: "list"; ordered: boolean; items: HelpSpan[][] }
  | { kind: "tip"; spans: HelpSpan[] }
  | { kind: "table"; header: HelpSpan[][]; rows: HelpSpan[][][] };

const ARTICLE_SLUG = /^[a-z0-9]+(-[a-z0-9]+)*$/;
const EXTERNAL = /^https:\/\/[^\s<>"]+$/;
const LINK = /^\[([^\]]+)\]\(([^)\s]+)\)/;

/** What a link's target names, or null (the link stays text). */
export function linkTarget(target: string): HelpLinkTarget | null {
  if (target.startsWith("cabinet:")) {
    const page = cabinetPage(target.slice("cabinet:".length));
    return page ? { kind: "cabinet", page } : null;
  }
  if (EXTERNAL.test(target)) {
    return { kind: "external", href: target };
  }
  return ARTICLE_SLUG.test(target) ? { kind: "article", slug: target } : null;
}

/** One line of text as spans: `code`, **bold** (only when closed) and [links](target). */
export function parseHelpInline(text: string): HelpSpan[] {
  const spans: HelpSpan[] = [];
  let plain = "";
  let bold = false;
  const flush = () => {
    if (plain !== "") {
      spans.push({ text: plain, bold, code: false, link: null });
      plain = "";
    }
  };

  let index = 0;
  while (index < text.length) {
    const rest = text.slice(index);
    if (rest.startsWith("`")) {
      const end = text.indexOf("`", index + 1);
      if (end > index + 1) {
        flush();
        spans.push({ text: text.slice(index + 1, end), bold, code: true, link: null });
        index = end + 1;
        continue;
      }
    }
    if (rest.startsWith("**") && (bold || text.includes("**", index + 2))) {
      flush();
      bold = !bold;
      index += 2;
      continue;
    }
    const link = LINK.exec(rest);
    if (link) {
      flush();
      const label = (link[1] ?? "").replaceAll("**", "");
      spans.push({ text: label, bold, code: false, link: linkTarget(link[2] ?? "") });
      index += link[0].length;
      continue;
    }
    plain += text.charAt(index);
    index += 1;
  }
  flush();
  return spans;
}

function tableCells(line: string): string[] {
  return line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => cell.trim());
}

const TABLE_SEPARATOR = /^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?$/;
const BULLET = /^[-*]\s+(.*)$/;
const NUMBERED = /^\d{1,3}[.)]\s+(.*)$/;
const HEADING = /^(#{2,3})\s+(.*?)\s*#*$/;

function isBlockStart(line: string): boolean {
  const trimmed = line.trim();
  return HEADING.test(trimmed) || BULLET.test(trimmed) || NUMBERED.test(trimmed) || /^(>|\|)/.test(trimmed);
}

/** The list starting at `start`: its items (a line indented under an item continues it) and the next line. */
function readList(lines: readonly string[], start: number, pattern: RegExp): { items: string[]; next: number } {
  const items: string[] = [];
  let index = start;
  while (index < lines.length) {
    const line = lines[index] ?? "";
    const item = pattern.exec(line.trim());
    if (item) {
      items.push((item[1] ?? "").trim());
    } else if (line.trim() !== "" && /^\s{2,}/.test(line) && items.length > 0) {
      items[items.length - 1] = `${items[items.length - 1] ?? ""} ${line.trim()}`;
    } else {
      break;
    }
    index += 1;
  }
  return { items, next: index };
}

export function parseHelpMarkdown(source: string): HelpBlock[] {
  const lines = source.replace(/\r\n?/g, "\n").split("\n");
  const blocks: HelpBlock[] = [];
  let index = 0;
  const at = (position: number): string => lines[position] ?? "";

  while (index < lines.length) {
    const trimmed = at(index).trim();
    if (trimmed === "") {
      index += 1;
      continue;
    }

    const heading = HEADING.exec(trimmed);
    if (heading) {
      const level = (heading[1] ?? "##").length === 2 ? 2 : 3;
      blocks.push({ kind: "heading", level, spans: parseHelpInline(heading[2] ?? "") });
      index += 1;
      continue;
    }

    if (trimmed.startsWith(">")) {
      const parts: string[] = [];
      while (index < lines.length && at(index).trim().startsWith(">")) {
        parts.push(at(index).trim().replace(/^>\s?/, ""));
        index += 1;
      }
      blocks.push({ kind: "tip", spans: parseHelpInline(parts.filter(Boolean).join(" ")) });
      continue;
    }

    const ordered = NUMBERED.test(trimmed);
    if (ordered || BULLET.test(trimmed)) {
      const { items, next } = readList(lines, index, ordered ? NUMBERED : BULLET);
      blocks.push({ kind: "list", ordered, items: items.map(parseHelpInline) });
      index = next;
      continue;
    }

    if (trimmed.startsWith("|") && TABLE_SEPARATOR.test(at(index + 1).trim())) {
      const header = tableCells(trimmed).map(parseHelpInline);
      index += 2;
      const rows: HelpSpan[][][] = [];
      while (index < lines.length && at(index).trim().startsWith("|")) {
        rows.push(tableCells(at(index)).map(parseHelpInline));
        index += 1;
      }
      blocks.push({ kind: "table", header, rows });
      continue;
    }

    const paragraph: string[] = [trimmed];
    index += 1;
    while (index < lines.length && at(index).trim() !== "" && !isBlockStart(at(index))) {
      paragraph.push(at(index).trim());
      index += 1;
    }
    blocks.push({ kind: "paragraph", spans: parseHelpInline(paragraph.join(" ")) });
  }
  return blocks;
}

/** Every link target of an article, for the check that each one exists. */
export function articleLinks(source: string): string[] {
  return [...source.matchAll(/\]\(([^)\s]+)\)/g)].map((match) => match[1] ?? "");
}
