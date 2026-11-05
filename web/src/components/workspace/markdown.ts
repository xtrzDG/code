/**
 * A small, safe Markdown reader for documents we ship ourselves (the data
 * processing agreement): headings, paragraphs, bullet lists, quotes,
 * tables and **bold**. It returns plain data; React renders it as text, so
 * nothing in the document can inject HTML.
 */

export interface InlineSpan {
  text: string;
  bold: boolean;
}

export type MarkdownBlock =
  | { kind: "heading"; level: 1 | 2 | 3; spans: InlineSpan[] }
  | { kind: "paragraph"; spans: InlineSpan[] }
  | { kind: "list"; items: InlineSpan[][] }
  | { kind: "quote"; paragraphs: InlineSpan[][] }
  | { kind: "table"; header: InlineSpan[][]; rows: InlineSpan[][][] };

/** "a **b** c" -> [a ][b, bold][ c]; an unmatched ** stays as text. */
export function parseInline(text: string): InlineSpan[] {
  const spans: InlineSpan[] = [];
  const parts = text.split("**");
  const hasClosing = parts.length % 2 === 1;
  parts.forEach((part, index) => {
    const isBold = hasClosing && index % 2 === 1;
    const value = !hasClosing && index > 0 ? `**${part}` : part;
    if (value !== "") {
      spans.push({ text: value, bold: isBold });
    }
  });
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

export function parseMarkdown(source: string): MarkdownBlock[] {
  const lines = source.replace(/\r\n?/g, "\n").split("\n");
  const blocks: MarkdownBlock[] = [];
  let index = 0;

  const at = (position: number): string => lines[position] ?? "";
  const isBlockStart = (line: string) => /^(#{1,3}\s|-\s|>|\|)/.test(line.trim());

  while (index < lines.length) {
    const trimmed = at(index).trim();
    if (trimmed === "") {
      index += 1;
      continue;
    }

    const heading = /^(#{1,3})\s+(.*?)\s*#*$/.exec(trimmed);
    if (heading) {
      blocks.push({ kind: "heading", level: (heading[1] ?? "#").length as 1 | 2 | 3, spans: parseInline(heading[2] ?? "") });
      index += 1;
      continue;
    }

    if (trimmed.startsWith(">")) {
      const paragraphs: string[][] = [[]];
      while (index < lines.length && at(index).trim().startsWith(">")) {
        const text = at(index).trim().replace(/^>\s?/, "");
        if (text === "") {
          paragraphs.push([]);
        } else {
          paragraphs[paragraphs.length - 1]?.push(text);
        }
        index += 1;
      }
      blocks.push({
        kind: "quote",
        paragraphs: paragraphs.filter((paragraph) => paragraph.length > 0).map((paragraph) => parseInline(paragraph.join(" "))),
      });
      continue;
    }

    if (trimmed.startsWith("- ")) {
      const items: string[] = [];
      while (index < lines.length) {
        const current = at(index);
        if (current.trim().startsWith("- ")) {
          items.push(current.trim().slice(2).trim());
        } else if (current.trim() !== "" && /^\s{2,}/.test(current) && items.length > 0) {
          items[items.length - 1] = `${items[items.length - 1] ?? ""} ${current.trim()}`;
        } else {
          break;
        }
        index += 1;
      }
      blocks.push({ kind: "list", items: items.map(parseInline) });
      continue;
    }

    if (trimmed.startsWith("|") && index + 1 < lines.length && TABLE_SEPARATOR.test(at(index + 1).trim())) {
      const header = tableCells(trimmed).map(parseInline);
      index += 2;
      const rows: InlineSpan[][][] = [];
      while (index < lines.length && at(index).trim().startsWith("|")) {
        rows.push(tableCells(at(index)).map(parseInline));
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
    blocks.push({ kind: "paragraph", spans: parseInline(paragraph.join(" ")) });
  }
  return blocks;
}
