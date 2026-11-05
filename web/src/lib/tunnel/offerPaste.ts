/**
 * Lines of an offer pasted from a spreadsheet or a list into the offer
 * table: one item per line, its cells separated by tabs (what Excel,
 * Google Sheets and Numbers put on the clipboard) in the table's order:
 * name, price, duration in minutes. A list without tabs gives names only.
 * A heading line ("Name  Price") is left out. Prices keep the number as
 * written ("18,50 ₾" → "18,50"), so the table's own checks apply to them.
 */

export interface PastedOffer {
  title: string;
  price: string;
  duration: string;
}

/** The most lines one paste adds (a whole menu, not a whole database). */
export const MAX_PASTED_LINES = 200;

const MAX_TITLE_LENGTH = 200;

/** Keeps the number of a price cell: digits, separators and grouping ("1 200,50"). */
function priceText(cell: string): string {
  return cell.replace(/[^\d.,\s']/g, "").trim();
}

/** Minutes from "45", "45 min" or "1:30". */
function durationText(cell: string): string {
  const clock = /^(\d{1,2}):(\d{2})$/.exec(cell.trim());
  if (clock) {
    return String(Number(clock[1]) * 60 + Number(clock[2]));
  }
  const minutes = /\d+/.exec(cell);
  return minutes ? String(Number(minutes[0])) : "";
}

/** A heading line: its price cell is words, not a number. */
function isHeading(cells: readonly string[]): boolean {
  const price = cells[1]?.trim() ?? "";
  return price !== "" && !/\d/.test(price);
}

/**
 * The items in pasted text, or null when it is a single value (pasted into
 * a field as usual). Empty lines and lines without a name are skipped.
 */
export function parsePastedOffer(text: string): PastedOffer[] | null {
  const lines = text.replace(/\r\n?/g, "\n").replace(/\n+$/, "").split("\n");
  if (lines.length < 2 && !text.includes("\t")) {
    return null;
  }
  const rows = lines.map((line) => line.split("\t"));
  const body = rows.length > 1 && rows[0] && isHeading(rows[0]) ? rows.slice(1) : rows;
  const offers = body
    .map(([title = "", price = "", duration = ""]) => ({
      title: title.trim().slice(0, MAX_TITLE_LENGTH),
      price: priceText(price),
      duration: durationText(duration),
    }))
    .filter((offer) => offer.title !== "");
  return offers.slice(0, MAX_PASTED_LINES);
}
