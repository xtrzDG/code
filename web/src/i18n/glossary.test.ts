/**
 * The cabinet's words, checked on the dictionaries themselves (this was the
 * screenshot tour's lint-texts step; a dictionary test catches the same
 * mistakes before anything is rendered):
 *
 * - every text is in its own language's script: no Cyrillic in English or
 *   Georgian, no Georgian in English or Russian, and no Russian or Georgian
 *   text that is mostly Latin words (brands and codes aside);
 * - the Russian glossary: the assistant is "помощник", never "ассистент"
 *   (the brand name aside), and versions and autotests are words of the
 *   Assistant's "Дополнительно" pages (and the platform admin) only;
 *   elsewhere an owner applies changes, sees updates and checks.
 *
 * The public landing page and its words are its own; the rules here are
 * for the cabinet.
 */

import { describe, expect, it } from "vitest";

import { en } from "./messages/en";
import { ka } from "./messages/ka";
import { ru } from "./messages/ru";
import type { MessageTree } from "./translate";

type Leaf = { path: string; text: string };

function leaves(tree: MessageTree, prefix = ""): Leaf[] {
  return Object.entries(tree).flatMap(([key, value]) =>
    typeof value === "string" ? [{ path: `${prefix}${key}`, text: value }] : value ? leaves(value, `${prefix}${key}.`) : [],
  );
}

/** Namespaces outside the cabinet (the public landing page). */
const NOT_CABINET = new Set(["landing"]);

/** The Assistant's advanced pages (updates, checks) and the platform admin, where versions and autotests are named. */
const ADVANCED = new Set(["assistant", "admin", "adminSecurity"]);

const namespaceOf = (path: string) => path.split(".")[0] ?? "";

/** The product's own name ("Мастерская ассистентов") and its short form on the home screen. */
const BRAND_KEYS = new Set(["common.appName", "app.shortName"]);

function cabinetLeaves(tree: MessageTree): Leaf[] {
  return leaves(tree).filter((leaf) => !NOT_CABINET.has(namespaceOf(leaf.path)));
}

/** Brand, product and format names written in Latin letters in every language. */
const LATIN_NAMES = new Set(
  (
    "WhatsApp Telegram Instagram Messenger Facebook Meta Google Calendar Business Manager Maps SMS PDF QR PNG SVG GEL EUR USD AI API URL CSV ID OK " +
    "Wi-Fi Viber Loyverse Cloudbeds Mews HotelRunner Cal.com Flitt Zadarma ElevenLabs Twilio BotFather Enter Esc Tab PWA iOS Android Chrome Safari " +
    "e-mail email DPA GDPR HTML JS iframe widget.js script Push VAT CRM Pro Plus Assistant Workshop Mtsvane Ezo Studio Lindenblatt Poster Booking.com " +
    "Airbnb Expedia TripAdvisor Yelp Wolt Glovo Bolt Uber Stripe PayPal Apple Pay Shortcuts Home Screen Share UTC GMT STOP START utility iPhone iPad"
  ).split(" "),
);

/** The text people read: placeholders, links, addresses and code samples left out. */
function prose(text: string): string {
  return text
    .replace(/\{[^}]*\}/g, " ")
    .replace(/https?:\/\/\S+|[\w.+-]+@[\w-]+\.[\w.]+|`[^`]*`|<[^>]*>/g, " ")
    .replace(/[a-z0-9]+(_[a-z0-9]+)+/g, " ");
}

function mostlyLatin(text: string): boolean {
  // "WhatsApp-ით", "QR-код": a brand with a native ending or noun is two words here.
  const words = prose(text).replace(/\be-mail\b/gi, "email").match(/[\p{L}][\p{L}.']*/gu) ?? [];
  const foreign = words.filter((word) => /^[A-Za-z]/.test(word) && word.length >= 3 && !LATIN_NAMES.has(word) && !/^[A-Z0-9.-]+$/.test(word));
  return foreign.length > 0 && foreign.length >= Math.ceil(words.length / 2);
}

const CYRILLIC = /[А-Яа-яЁё]{3,}/;
const GEORGIAN = /[Ⴀ-ჿ]{3,}/;

function offenders(tree: MessageTree, isWrong: (text: string) => boolean): string[] {
  return cabinetLeaves(tree)
    .filter((leaf) => isWrong(prose(leaf.text)))
    .map((leaf) => `${leaf.path}: ${leaf.text}`);
}

describe("texts are in their own language", () => {
  it("English has no Russian or Georgian", () => {
    expect(offenders(en, (text) => CYRILLIC.test(text) || GEORGIAN.test(text))).toEqual([]);
  });

  it("Russian has no Georgian and no text that is mostly Latin words", () => {
    expect(offenders(ru, (text) => GEORGIAN.test(text))).toEqual([]);
    expect(offenders(ru, mostlyLatin)).toEqual([]);
  });

  it("Georgian has no Russian and no text that is mostly Latin words", () => {
    expect(offenders(ka, (text) => CYRILLIC.test(text))).toEqual([]);
    expect(offenders(ka, mostlyLatin)).toEqual([]);
  });
});

describe("the Russian glossary", () => {
  const texts = cabinetLeaves(ru);

  it("calls the assistant 'помощник'", () => {
    const wrong = texts.filter((leaf) => /ассистент/i.test(leaf.text) && !BRAND_KEYS.has(leaf.path));
    expect(wrong.map((leaf) => `${leaf.path}: ${leaf.text}`)).toEqual([]);
  });

  it("names versions and autotests only on the advanced pages (legal documents keep their versions)", () => {
    const wrong = texts.filter(
      (leaf) =>
        !ADVANCED.has(namespaceOf(leaf.path)) &&
        (/автотест|автопровер/i.test(leaf.text) || (/верси[яиюйе]/i.test(leaf.text) && !/(^|\.)dpa[A-Za-z]*\.|document/i.test(leaf.path))),
    );
    expect(wrong.map((leaf) => `${leaf.path}: ${leaf.text}`)).toEqual([]);
  });
});
