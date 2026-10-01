/**
 * A small Tailwind class merge for UI kit components: a caller's className
 * replaces the component's own classes of the same kind instead of competing
 * with them in the stylesheet order.
 *
 *     mergeClassOverrides("w-full h-10 text-ink hover:bg-surface-muted", "w-32 hover:bg-danger-soft")
 *     // → "h-10 text-ink w-32 hover:bg-danger-soft"
 *
 * Only the groups that callers override in practice are known: width and
 * height, text, background and border colours, font size, corner radius and
 * horizontal/vertical padding, each per variant (`hover:`, `sm:` …). Every
 * other class is kept as it is.
 */

const FONT_SIZES = new Set(["xs", "sm", "base", "lg", "xl", "2xl", "3xl", "4xl", "5xl", "6xl", "7xl", "8xl", "9xl"]);
const TEXT_NOT_COLOUR = new Set([
  "left",
  "center",
  "right",
  "justify",
  "start",
  "end",
  "wrap",
  "nowrap",
  "balance",
  "pretty",
  "ellipsis",
  "clip",
]);
const BACKGROUND_NOT_COLOUR = /^(fixed|local|scroll|clip-.*|origin-.*|repeat.*|no-repeat|auto|cover|contain|center|top|bottom|left|right|left-.*|right-.*|none|linear-.*|radial.*|conic.*|gradient-.*|blend-.*)$/;
const BORDER_STYLES = new Set(["solid", "dashed", "dotted", "double", "hidden", "none", "collapse", "separate", "spacing"]);
const BORDER_SIDES = /^(x|y|t|r|b|l|s|e)(-|$)/;

/** Splits "sm:hover:text-ink!" into its variants ("sm:hover:") and the utility ("text-ink"). */
function splitVariants(token: string): { variants: string; utility: string } {
  let depth = 0;
  let lastColon = -1;
  for (let index = 0; index < token.length; index += 1) {
    const character = token[index];
    if (character === "[" || character === "(") {
      depth += 1;
    } else if (character === "]" || character === ")") {
      depth -= 1;
    } else if (character === ":" && depth === 0) {
      lastColon = index;
    }
  }
  const utility = token.slice(lastColon + 1).replace(/^!/, "").replace(/!$/, "");
  return { variants: token.slice(0, lastColon + 1), utility };
}

const SIMPLE_PREFIXES = ["min-w", "max-w", "min-h", "max-h", "w", "h", "px", "py"] as const;

/** "w", "text-colour" … for the utilities this merge knows, else null. */
export function classGroup(utility: string): string | null {
  const plain = utility.replace(/^-/, "");
  if (plain === "rounded") {
    return "rounded";
  }
  for (const prefix of SIMPLE_PREFIXES) {
    if (plain.startsWith(`${prefix}-`)) {
      return prefix;
    }
  }
  const dash = plain.indexOf("-");
  if (dash < 0) {
    return null;
  }
  const prefix = plain.slice(0, dash);
  const value = plain.slice(dash + 1);
  switch (prefix) {
    case "text":
      if (FONT_SIZES.has(value) || /^\[\d/.test(value)) {
        return "font-size";
      }
      return TEXT_NOT_COLOUR.has(value) ? null : "text-colour";
    case "bg":
      return BACKGROUND_NOT_COLOUR.test(value) ? null : "background-colour";
    case "border":
      if (BORDER_STYLES.has(value) || BORDER_SIDES.test(value) || /^\d|^\[\d/.test(value)) {
        return null;
      }
      return "border-colour";
    case "rounded":
      // rounded-t-lg and friends round one side only.
      return /^(t|r|b|l|s|e|tl|tr|br|bl|ss|se|es|ee)(-|$)/.test(value) ? null : "rounded";
    default:
      return null;
  }
}

function conflictKey(token: string): string | null {
  const { variants, utility } = splitVariants(token);
  const group = classGroup(utility);
  return group === null ? null : `${variants}${group}`;
}

/** `base` without the classes `overrides` replaces, followed by `overrides`. */
export function mergeClassOverrides(base: string, overrides: string | null | undefined): string {
  const overrideTokens = (overrides ?? "").split(/\s+/).filter(Boolean);
  if (overrideTokens.length === 0) {
    return base;
  }
  const replaced = new Set(overrideTokens.map(conflictKey).filter((key): key is string => key !== null));
  const kept = base.split(/\s+/).filter((token) => {
    if (!token) {
      return false;
    }
    const key = conflictKey(token);
    return key === null || !replaced.has(key);
  });
  return [...kept, ...overrideTokens].join(" ");
}
