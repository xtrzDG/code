/**
 * Physical-direction Tailwind classes and their logical twins.
 *
 * The cabinet reads right to left in Hebrew (`<html dir="rtl">`), so a
 * class that names a side of the screen (`ml-2`, `left-0`, `text-left`,
 * `rounded-r-lg`) must name a side of the text instead (`ms-2`, `start-0`,
 * `text-start`, `rounded-e-lg`): the browser then mirrors the layout by
 * itself. `scripts/rtl-codemod.mjs` rewrites a file with these rules and
 * `logicalClasses.policy.test.ts` keeps new physical classes out of src/.
 *
 * Left alone on purpose:
 *
 * - a class under the `rtl:` or `ltr:` variant: it already says which
 *   direction it is for;
 * - `left-1/2` beside `-translate-x-1/2` on the same line: the centring
 *   idiom, which centres in both directions;
 * - `translate-x-*`, `origin-*` and gradients: they need a person's choice
 *   (a sliding knob mirrors, a centred box does not), so they get explicit
 *   `rtl:` twins where the direction matters.
 *
 * This module is imported by the Node codemod too: no path aliases and
 * only type syntax Node can strip.
 */

/** Exact classes and their twins. */
const EXACT: ReadonlyMap<string, string> = new Map([
  ["text-left", "text-start"],
  ["text-right", "text-end"],
  ["float-left", "float-start"],
  ["float-right", "float-end"],
  ["clear-left", "clear-start"],
  ["clear-right", "clear-end"],
]);

type ValueKind = "spacing" | "border" | "radius";

interface Family {
  physical: string;
  logical: string;
  value: ValueKind;
  /** Whether the class may stand without a value (`border-l`, `rounded-r`). */
  bare: boolean;
}

const family = (physical: string, logical: string, value: ValueKind, bare = false): Family => ({ physical, logical, value, bare });

/** Longest prefixes first, so `rounded-tl` is not read as `rounded-t…`. */
const FAMILIES: readonly Family[] = [
  family("scroll-ml", "scroll-ms", "spacing"),
  family("scroll-mr", "scroll-me", "spacing"),
  family("scroll-pl", "scroll-ps", "spacing"),
  family("scroll-pr", "scroll-pe", "spacing"),
  family("rounded-tl", "rounded-ss", "radius", true),
  family("rounded-tr", "rounded-se", "radius", true),
  family("rounded-bl", "rounded-es", "radius", true),
  family("rounded-br", "rounded-ee", "radius", true),
  family("rounded-l", "rounded-s", "radius", true),
  family("rounded-r", "rounded-e", "radius", true),
  family("border-l", "border-s", "border", true),
  family("border-r", "border-e", "border", true),
  family("ml", "ms", "spacing"),
  family("mr", "me", "spacing"),
  family("pl", "ps", "spacing"),
  family("pr", "pe", "spacing"),
  family("left", "start", "spacing"),
  family("right", "end", "spacing"),
];

const ARBITRARY = String.raw`\[[^\]\s]+\]|\([^)\s]+\)`;
const VALUE_PATTERNS: Readonly<Record<ValueKind, RegExp>> = {
  spacing: new RegExp(String.raw`^(?:\d+(?:\.\d+)?|\d+/\d+|px|auto|full|${ARBITRARY})$`),
  border: new RegExp(String.raw`^(?:\d+|px|${ARBITRARY}|[a-z]+(?:-[a-z0-9]+)*(?:/\d+)?)$`),
  radius: new RegExp(String.raw`^(?:none|xs|sm|md|lg|xl|2xl|3xl|4xl|full|${ARBITRARY})$`),
};

/** Variants that already name a direction. */
const DIRECTION_VARIANT = /(^|:)(rtl|ltr):$/;

interface ClassParts {
  variants: string;
  important: string;
  negative: string;
  utility: string;
  trailingImportant: string;
}

/** "md:hover:-ml-2!" -> variants "md:hover:", negative "-", utility "ml-2", trailing "!". */
function splitClass(token: string): ClassParts | null {
  let depth = 0;
  let variantsEnd = 0;
  for (let index = 0; index < token.length; index += 1) {
    const character = token[index];
    if (character === "[" || character === "(") {
      depth += 1;
    } else if (character === "]" || character === ")") {
      depth -= 1;
    } else if (character === ":" && depth === 0) {
      variantsEnd = index + 1;
    }
  }
  const match = /^(!?)(-?)([a-z][a-z0-9-]*(?:-(?:\[[^\]\s]+\]|\([^)\s]+\)|[\w./]+))?)(!?)$/.exec(token.slice(variantsEnd));
  if (!match) {
    return null;
  }
  return {
    variants: token.slice(0, variantsEnd),
    important: match[1] ?? "",
    negative: match[2] ?? "",
    utility: match[3] ?? "",
    trailingImportant: match[4] ?? "",
  };
}

function logicalUtility(utility: string, negative: string): string | null {
  const exact = EXACT.get(utility);
  if (exact !== undefined) {
    return negative ? null : exact;
  }
  for (const entry of FAMILIES) {
    if (utility === entry.physical) {
      return entry.bare && !negative ? entry.logical : null;
    }
    if (utility.startsWith(`${entry.physical}-`)) {
      const value = utility.slice(entry.physical.length + 1);
      if (negative && entry.value !== "spacing") {
        return null;
      }
      return VALUE_PATTERNS[entry.value].test(value) ? `${entry.logical}-${value}` : null;
    }
  }
  return null;
}

/**
 * The logical twin of one class, or null when it names no side (or names
 * it under `rtl:`/`ltr:`): "pl-3" -> "ps-3", "md:-mr-1" -> "md:-me-1",
 * "border-l-line" -> "border-s-line", "rtl:left-2" -> null.
 */
export function logicalClass(token: string): string | null {
  const parts = splitClass(token);
  if (!parts || DIRECTION_VARIANT.test(parts.variants)) {
    return null;
  }
  const twin = logicalUtility(parts.utility, parts.negative);
  return twin === null ? null : `${parts.variants}${parts.important}${parts.negative}${twin}${parts.trailingImportant}`;
}

/** Characters around a class in source text: quotes, spaces, template braces. */
const TOKEN = /(?<=^|[\s"'`{}])[^\s"'`{}]+(?=$|[\s"'`{}])/g;
const CENTRING = /-translate-x-1\/2\b/;
const CENTRED_START = /(^|:)left-1\/2$/;

export interface PhysicalClass {
  /** 1-based line of the class. */
  line: number;
  found: string;
  logical: string;
}

function eachPhysicalClass(source: string, visit: (match: PhysicalClass, lineText: string, column: number) => void): void {
  source.split("\n").forEach((lineText, index) => {
    for (const match of lineText.matchAll(TOKEN)) {
      const found = match[0];
      const logical = logicalClass(found);
      if (logical === null) {
        continue;
      }
      if (CENTRED_START.test(found) && CENTRING.test(lineText)) {
        continue;
      }
      visit({ line: index + 1, found, logical }, lineText, match.index ?? 0);
    }
  });
}

/** Every physical-direction class of a source file, with its twin. */
export function findPhysicalClasses(source: string): PhysicalClass[] {
  const found: PhysicalClass[] = [];
  eachPhysicalClass(source, (match) => found.push(match));
  return found;
}

/** The source with every physical-direction class replaced by its twin. */
export function toLogicalClasses(source: string): string {
  const lines = source.split("\n");
  const replacements = new Map<number, { column: number; found: string; logical: string }[]>();
  eachPhysicalClass(source, (match, _lineText, column) => {
    const list = replacements.get(match.line) ?? [];
    list.push({ column, found: match.found, logical: match.logical });
    replacements.set(match.line, list);
  });
  for (const [line, list] of replacements) {
    let text = lines[line - 1] ?? "";
    for (const entry of [...list].sort((left, right) => right.column - left.column)) {
      text = text.slice(0, entry.column) + entry.logical + text.slice(entry.column + entry.found.length);
    }
    lines[line - 1] = text;
  }
  return lines.join("\n");
}
