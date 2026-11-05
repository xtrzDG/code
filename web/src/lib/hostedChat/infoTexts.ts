/**
 * Texts of the hosted chat page's information panel (the page as a "link
 * in bio": hours, address, a Book button), in the languages of the page's
 * other texts (texts.ts). `{time}` and `{day}` are filled in; a language
 * without texts falls back to English.
 */

import { INFO_TEXTS_ASIA } from "./infoTextsAsia";
import { INFO_TEXTS_CENTRAL } from "./infoTextsCentral";
import { INFO_TEXTS_WEST } from "./infoTextsWest";
import { primaryLanguage } from "./language";

export interface HostedInfoTexts {
  openNow: string;
  closedNow: string;
  openAllDay: string;
  /** "until {time}" */
  until: string;
  /** "opens at {time}" (later today) */
  opensAt: string;
  /** "opens tomorrow at {time}" */
  opensTomorrow: string;
  /** "opens {day} at {time}" (a weekday name) */
  opensOn: string;
  hours: string;
  /** A day without hours. */
  closed: string;
  address: string;
  openMap: string;
  book: string;
  /** What the Book button writes into the chat for the visitor to send. */
  bookPrompt: string;
  /** The phone's toggle for the hours and the address. */
  details: string;
}

export const HOSTED_INFO_TEXTS: Readonly<Record<string, HostedInfoTexts>> = {
  ...INFO_TEXTS_WEST,
  ...INFO_TEXTS_CENTRAL,
  ...INFO_TEXTS_ASIA,
};

const ENGLISH = INFO_TEXTS_WEST.en as HostedInfoTexts;

export function hostedInfoTexts(tag: string): HostedInfoTexts {
  return HOSTED_INFO_TEXTS[primaryLanguage(tag)] ?? ENGLISH;
}

/** "opens {day} at {time}" with its values. */
export function fillText(template: string, values: Readonly<Record<string, string>>): string {
  return template.replace(/\{(\w+)\}/g, (whole, name: string) => values[name] ?? whole);
}
