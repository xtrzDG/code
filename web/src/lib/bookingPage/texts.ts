/**
 * Texts of a guest's booking page (/r/{token}), in the guest's language:
 * the languages of the written booking confirmation (English is the
 * fallback). They are customer texts, like the hosted chat page's
 * (lib/hostedChat/texts.ts), not the cabinet's dictionaries. `{business}`
 * and `{when}` are filled in.
 */

import { primaryLanguage } from "../hostedChat/language";
import { TEXTS_EAST } from "./textsEast";
import { TEXTS_MIDDLE } from "./textsMiddle";
import { TEXTS_WEST } from "./textsWest";

export interface BookingPageTexts {
  pageTitle: string;
  statusPending: string;
  statusConfirmed: string;
  statusCancelled: string;
  statusCompleted: string;
  statusNoShow: string;
  when: string;
  arrival: string;
  departure: string;
  guests: string;
  service: string;
  address: string;
  openMap: string;
  phone: string;
  policy: string;
  addToCalendar: string;
  writeToUs: string;
  chat: string;
  call: string;
  change: string;
  cancel: string;
  cancelTitle: string;
  cancelText: string;
  keep: string;
  confirmCancel: string;
  cancelling: string;
  cancelledNotice: string;
  newTime: string;
  date: string;
  freeTimes: string;
  noTimes: string;
  closedDay: string;
  stayFree: string;
  stayTaken: string;
  loadingTimes: string;
  moveTo: string;
  moving: string;
  close: string;
  movedNotice: string;
  overNotice: string;
  startedNotice: string;
  errorTitle: string;
  linkInvalid: string;
  linkExpired: string;
  bookingChanged: string;
  notActive: string;
  alreadyStarted: string;
  taken: string;
  closedTime: string;
  tooMany: string;
  generic: string;
}

export const BOOKING_PAGE_TEXTS: Readonly<Record<string, BookingPageTexts>> = {
  ...TEXTS_WEST,
  ...TEXTS_MIDDLE,
  ...TEXTS_EAST,
};

/** The languages with texts, for matching a browser's languages. */
export const BOOKING_PAGE_LANGUAGES: readonly string[] = Object.keys(BOOKING_PAGE_TEXTS);

const ENGLISH = TEXTS_WEST.en as BookingPageTexts;

/** The texts of a language tag ("pt-BR" uses "pt"); English when there are none. */
export function bookingPageTexts(tag: string): BookingPageTexts {
  return BOOKING_PAGE_TEXTS[primaryLanguage(tag)] ?? ENGLISH;
}

/** True when the page speaks `tag` itself (not the English fallback). */
export function hasBookingPageTexts(tag: string): boolean {
  return primaryLanguage(tag) in BOOKING_PAGE_TEXTS;
}
