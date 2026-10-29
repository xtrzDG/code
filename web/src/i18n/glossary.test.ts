/**
 * The cabinet's words, checked on the dictionaries themselves (this was the
 * screenshot tour's lint-texts step; a dictionary test catches the same
 * mistakes before anything is rendered):
 *
 * - every text is in its own script: no Cyrillic, Georgian or Hebrew in
 *   English or Italian (the languages of the cabinet);
 * - the Italian glossary: the assistant is "assistente" (never a helper), and
 *   versions and autotests are words of the Assistant's advanced pages (and
 *   the platform admin) only; elsewhere an owner applies changes, sees
 *   updates and checks.
 *
 * The public landing page and its words are its own; the rules here are
 * for the cabinet.
 */

import { describe, expect, it } from "vitest";

import { en } from "./messages/en";
import { it as italian } from "./messages/it";
import type { MessageTree } from "./translate";

type Leaf = { path: string; text: string };

function leaves(tree: MessageTree, prefix = ""): Leaf[] {
  return Object.entries(tree).flatMap(([key, value]) =>
    typeof value === "string" ? [{ path: `${prefix}${key}`, text: value }] : value ? leaves(value, `${prefix}${key}.`) : [],
  );
}

/** Namespaces outside the cabinet (the public landing page). */
const NOT_CABINET = new Set(["landing"]);

/** The Assistant's advanced pages (updates, checks), the niche editor and the platform admin, where versions and autotests are named. */
const ADVANCED = new Set(["assistant", "admin", "adminSecurity", "adminSystem", "adminNiches"]);

const namespaceOf = (path: string) => path.split(".")[0] ?? "";

function cabinetLeaves(tree: MessageTree): Leaf[] {
  return leaves(tree).filter((leaf) => !NOT_CABINET.has(namespaceOf(leaf.path)));
}

/** The text people read: placeholders, links, addresses and code samples left out. */
function prose(text: string): string {
  return text
    .replace(/\{[^}]*\}/g, " ")
    .replace(/https?:\/\/\S+|[\w.+-]+@[\w-]+\.[\w.]+|`[^`]*`|<[^>]*>/g, " ")
    .replace(/[a-z0-9]+(_[a-z0-9]+)+/g, " ");
}

const CYRILLIC = /[А-Яа-яЁё]{3,}/;
const GEORGIAN = /[Ⴀ-ჿ]{3,}/;
const HEBREW = /[֐-׿]{3,}/;

const otherScript = (text: string) => CYRILLIC.test(text) || GEORGIAN.test(text) || HEBREW.test(text);

function offenders(tree: MessageTree, isWrong: (text: string) => boolean): string[] {
  return cabinetLeaves(tree)
    .filter((leaf) => isWrong(prose(leaf.text)))
    .map((leaf) => `${leaf.path}: ${leaf.text}`);
}

describe("texts are in their own language", () => {
  it("English has no Russian, Georgian or Hebrew", () => {
    expect(offenders(en, otherScript)).toEqual([]);
  });

  it("Italian has no Russian, Georgian or Hebrew", () => {
    expect(offenders(italian, otherScript)).toEqual([]);
  });
});

describe("the Italian glossary", () => {
  const texts = cabinetLeaves(italian);

  it("calls the assistant 'assistente', never a helper", () => {
    const wrong = texts.filter((leaf) => /\baiutant[ei]\b/i.test(prose(leaf.text)));
    expect(wrong.map((leaf) => `${leaf.path}: ${leaf.text}`)).toEqual([]);
    expect(italian.common.tagline).toContain("assistente");
  });

  it("names versions and autotests only on the advanced pages (legal documents keep their versions)", () => {
    const wrong = texts.filter(
      (leaf) =>
        !ADVANCED.has(namespaceOf(leaf.path)) &&
        (/test automatic/i.test(leaf.text) || (/\bversion[ei]\b/i.test(leaf.text) && !/(^|\.)dpa[A-Za-z]*\.|document|legal/i.test(leaf.path))),
    );
    expect(wrong.map((leaf) => `${leaf.path}: ${leaf.text}`)).toEqual([]);
  });
});

describe("every text the cabinet's pages carry", () => {
  // A cabinet page holds its dictionary, and the DAST scan's rule 10099
  // (.github/workflows/zap.yml) reads "the package costs {price}" as an
  // ActionScript 3.0 declaration, `package <name> {`: a Medium finding.
  const ACTIONSCRIPT_PACKAGE = /\bpackage\s+[a-z0-9.]+\s*\{/i;

  it("never reads as source code to the scan", () => {
    const wrong = [en, italian].flatMap((tree) => leaves(tree).filter((leaf) => ACTIONSCRIPT_PACKAGE.test(leaf.text)));
    expect(wrong.map((leaf) => `${leaf.path}: ${leaf.text}`)).toEqual([]);
  });
});
