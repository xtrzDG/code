/**
 * Intl for the cabinet's languages: every date, number, list, relative time
 * and plural form shown in a UI language comes from these factories.
 *
 * Georgian is formatted by our own CLDR tables (`georgian*.ts`), on the
 * server and in every browser: Chrome's Intl has no Georgian and writes "ka"
 * dates as American English ("8 hours ago", "Oct 16, 2026"), while the
 * server's Node writes Georgian, so the page would also change its text when
 * React hydrates it. Russian, English and every other locale use the
 * platform's Intl. Option sets the Georgian tables do not cover fall back to
 * the platform too.
 *
 * Fixed-format helpers that read calendar fields ("en-US" `formatToParts`)
 * may use Intl directly; `intlUsage.test.ts` keeps everything else here.
 */

import { georgianDateFormat } from "./georgianDates";
import {
  formatGeorgianList,
  georgianNumberFormat,
  georgianPluralCategory,
  georgianRelativeTimeFormat,
} from "./georgianNumbers";

export interface DateTimeFormatter {
  format(date: Date): string;
  formatRange(from: Date, to: Date): string;
}

export interface NumberFormatter {
  format(value: number): string;
}

export interface RelativeTimeFormatter {
  format(value: number, unit: Intl.RelativeTimeFormatUnit): string;
}

export interface ListFormatter {
  format(items: readonly string[]): string;
}

export interface PluralSelector {
  select(value: number): Intl.LDMLPluralRule;
}

/** "ka", "ka-GE", "KA_ge": the language Chrome cannot format. */
export function isGeorgianLocale(locale: string): boolean {
  return /^ka(?:[-_]|$)/i.test(locale);
}

export function dateTimeFormat(locale: string, options: Intl.DateTimeFormatOptions = {}): DateTimeFormatter {
  const georgian = isGeorgianLocale(locale) ? georgianDateFormat(options) : null;
  if (georgian) {
    return georgian;
  }
  const native = new Intl.DateTimeFormat(locale, options);
  return { format: (date) => native.format(date), formatRange: (from, to) => native.formatRange(from, to) };
}

export function numberFormat(locale: string, options: Intl.NumberFormatOptions = {}): NumberFormatter {
  const georgian = isGeorgianLocale(locale) ? georgianNumberFormat(options) : null;
  if (georgian) {
    return { format: georgian };
  }
  const native = new Intl.NumberFormat(locale, options);
  return { format: (value) => native.format(value) };
}

export function relativeTimeFormat(locale: string, options: Intl.RelativeTimeFormatOptions = {}): RelativeTimeFormatter {
  if (isGeorgianLocale(locale)) {
    return { format: georgianRelativeTimeFormat(options) };
  }
  const native = new Intl.RelativeTimeFormat(locale, options);
  return { format: (value, unit) => native.format(value, unit) };
}

export function listFormat(locale: string, options: Intl.ListFormatOptions = {}): ListFormatter {
  if (isGeorgianLocale(locale)) {
    return { format: (items) => formatGeorgianList(items, options.type) };
  }
  const native = new Intl.ListFormat(locale, options);
  return { format: (items) => native.format(items) };
}

/** Plural categories of cardinal numbers ("one", "few", "many", "other"). */
export function pluralRules(locale: string): PluralSelector {
  if (isGeorgianLocale(locale)) {
    return { select: georgianPluralCategory };
  }
  const native = new Intl.PluralRules(locale);
  return { select: (value) => native.select(value) };
}
