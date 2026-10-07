import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

import { fromSrc, publicClientModules } from "@/test/publicModules";

import { en } from "./messages/en";
import { PUBLIC_CLIENT_TEXTS, publicClientMessages } from "./publicScope";
import type { MessageTree } from "./translate";

/** Source without its comments (their examples name keys nobody reads). */
function withoutComments(source: string): string {
  return source.replace(/\/\*[\s\S]*?\*\//g, "").replace(/(^|\s)\/\/.*$/gm, "$1");
}

/**
 * The dictionary keys a module names, in t()/tp() calls and key literals:
 * "landing.pricing.country" whole, `errors.${code}` as its fixed part
 * ("errors"). Only keys of an existing section count.
 */
function keysNamedIn(source: string, sections: ReadonlySet<string>): Set<string> {
  const named = new Set<string>();
  for (const match of withoutComments(source).matchAll(/["'`]([a-z][A-Za-z0-9]*(?:\.[A-Za-z0-9_]+)*)(?:\.\$\{|["'`])/g)) {
    const key = match[1] ?? "";
    if (key.includes(".") || match[0].endsWith("{")) {
      if (sections.has(key.split(".")[0] ?? "")) {
        named.add(key);
      }
    }
  }
  return named;
}

const covers = (entry: string, key: string) => key === entry || key.startsWith(`${entry}.`);

describe("the public site's share of the dictionary", () => {
  const sections = new Set(Object.keys(en));
  const named = new Map<string, string[]>();
  // Lazily loaded modules too: they run on public pages all the same.
  const modules = publicClientModules({ lazy: true });
  for (const file of modules) {
    for (const key of keysNamedIn(readFileSync(file, "utf8"), sections)) {
      named.set(key, [...(named.get(key) ?? []), fromSrc(file)]);
    }
  }

  it("holds every text the public site's client modules name", () => {
    expect(modules.size).toBeGreaterThan(20);
    // A missing one would show as its key on a public page.
    const missing = [...named].filter(([key]) => !PUBLIC_CLIENT_TEXTS.some((entry) => covers(entry, key)));
    expect(Object.fromEntries(missing)).toEqual({});
  });

  it("holds nothing else: every entry is read by one of them", () => {
    // An entry nobody reads is text every visitor downloads for nothing.
    const unread = PUBLIC_CLIENT_TEXTS.filter((entry) => ![...named.keys()].some((key) => covers(entry, key)));
    expect(unread).toEqual([]);
  });

  it("names only texts the dictionary has", () => {
    for (const entry of PUBLIC_CLIENT_TEXTS) {
      expect(en, entry).toHaveProperty(entry.split("."));
    }
  });

  it("copies those texts in the dictionary's shape and leaves the cabinet's out", () => {
    const messages: MessageTree = {
      common: { save: "Save", cancel: "Cancel" },
      landing: { hero: { title: "Hi" }, pricing: { country: "Country", show: "Show", note: "-" } },
      knowledge: { title: "K", form: { priceAmbiguous: "?", priceTooPrecise: "!", other: "-" } },
      settings: { title: "Settings" },
    };
    expect(publicClientMessages(messages)).toEqual({
      common: { save: "Save", cancel: "Cancel" },
      landing: { pricing: { country: "Country", show: "Show" } },
      knowledge: { form: { priceAmbiguous: "?", priceTooPrecise: "!" } },
    });
    const picked = publicClientMessages(en as MessageTree);
    expect(picked).not.toHaveProperty("knowledge.title");
    expect(picked).not.toHaveProperty("landing.hero");
    // The point of it: a small part of what the cabinet needs.
    expect(JSON.stringify(picked).length).toBeLessThan(JSON.stringify(en).length / 10);
  });
});
