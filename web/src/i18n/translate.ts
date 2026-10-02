/**
 * Message lookup with fallback, interpolation and plurals.
 *
 * Keys are dotted paths into the dictionaries ("auth.sendCode"). A key
 * missing in the current language falls back to English, then to the key
 * itself, so a missing translation never breaks a page.
 */

import type { Locale } from "./config";
import type { en } from "./messages/en";

/** Plural forms of one text; languages use the categories they need. */
export type PluralForms = {
  zero?: string;
  one?: string;
  two?: string;
  few?: string;
  many?: string;
  other: string;
};

type Stringify<T> = {
  -readonly [Key in keyof T]: T[Key] extends string
    ? string
    : T[Key] extends { other: string }
      ? PluralForms
      : Stringify<T[Key]>;
};

/** The shape every dictionary must have (English is the reference). */
export type Messages = Stringify<typeof en>;

/** The translation of one section dictionary (see messages/sections/). */
export type Translation<T> = Stringify<T>;

type LeafPaths<T, Prefix extends string = ""> = {
  [Key in keyof T & string]: T[Key] extends string
    ? `${Prefix}${Key}`
    : T[Key] extends PluralForms
      ? never
      : LeafPaths<T[Key], `${Prefix}${Key}.`>;
}[keyof T & string];

type PluralPaths<T, Prefix extends string = ""> = {
  [Key in keyof T & string]: T[Key] extends string
    ? never
    : T[Key] extends PluralForms
      ? `${Prefix}${Key}`
      : PluralPaths<T[Key], `${Prefix}${Key}.`>;
}[keyof T & string];

/** Every translatable text: `t("businesses.title")`. */
export type MessageKey = LeafPaths<Messages>;

/** Texts with plural forms (`one`, `few`, `many`, `other`): `tp("x", 3)`. */
export type PluralKey = PluralPaths<Messages>;

export type MessageValues = Record<string, string | number>;

/** A partial dictionary is allowed at runtime; types require full ones. */
export type MessageTree = { [key: string]: string | MessageTree | undefined };

export interface Translator {
  locale: Locale;
  t: (key: MessageKey, values?: MessageValues) => string;
  tp: (key: PluralKey, count: number, values?: MessageValues) => string;
  /** For keys built at runtime (error codes, enum values). */
  has: (key: string) => boolean;
  /** Like `t`, for keys built at runtime; unknown keys return `fallback`. */
  tDynamic: (key: string, fallback: string, values?: MessageValues) => string;
}

export function lookupMessage(
  tree: MessageTree | undefined,
  key: string,
): string | MessageTree | undefined {
  let node: string | MessageTree | undefined = tree;
  for (const segment of key.split(".")) {
    if (node === undefined || typeof node === "string") {
      return undefined;
    }
    node = node[segment];
  }
  return node;
}

/**
 * Replace `{name}` placeholders; unknown placeholders stay as they are. A
 * value that already ends with a full stop (a Russian date "4 окт. 2026 г.")
 * takes the place of the template's own full stop right after it.
 */
export function interpolate(template: string, values?: MessageValues): string {
  if (!values) {
    return template;
  }

  return template.replace(/\{(\w+)\}(\.?)/g, (placeholder, name: string, stop: string) => {
    const value = values[name];
    if (value === undefined) {
      return placeholder;
    }

    const text = String(value);
    return text.endsWith(".") ? text : text + stop;
  });
}

/** Dictionaries merged key by key: `override` wins where it has a text. */
export function mergeMessages(base: MessageTree, override: MessageTree | undefined): MessageTree {
  if (!override) {
    return base;
  }

  const merged: MessageTree = { ...base };
  for (const [key, value] of Object.entries(override)) {
    const baseValue = base[key];
    if (typeof value === "string") {
      merged[key] = value;
    } else if (typeof baseValue === "object") {
      merged[key] = mergeMessages(baseValue, value);
    } else {
      merged[key] = value;
    }
  }
  return merged;
}

export function createTranslator(
  locale: Locale,
  messages: MessageTree,
  fallbackMessages?: MessageTree,
): Translator {
  const pluralRules = new Intl.PluralRules(locale);
  const numberFormat = new Intl.NumberFormat(locale);

  const resolveText = (key: string): string | undefined => {
    const primary = lookupMessage(messages, key);
    if (typeof primary === "string") {
      return primary;
    }
    const fallback = lookupMessage(fallbackMessages, key);
    return typeof fallback === "string" ? fallback : undefined;
  };

  const resolvePlural = (key: string, count: number): string | undefined => {
    const category = pluralRules.select(count);
    for (const tree of [messages, fallbackMessages]) {
      const forms = lookupMessage(tree, key);
      if (forms && typeof forms === "object") {
        const form = forms[category] ?? forms.other;
        if (typeof form === "string") {
          return form;
        }
      }
    }
    return undefined;
  };

  return {
    locale,
    t: (key, values) => interpolate(resolveText(key) ?? key, values),
    tp: (key, count, values) =>
      interpolate(resolvePlural(key, count) ?? key, {
        count: numberFormat.format(count),
        ...values,
      }),
    has: (key) => resolveText(key) !== undefined,
    tDynamic: (key, fallback, values) => interpolate(resolveText(key) ?? fallback, values),
  };
}
