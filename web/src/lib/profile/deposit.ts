/**
 * The booking deposit in the profile editor: typed as a price in the
 * business's currency ("20", "12,50"), stored in minor units with the
 * booking rules; empty means no deposit.
 */

import type { Schema } from "@/api/types";
import type { MessageKey } from "@/i18n/translate";

import { currencyFractionDigits, decimalInputValue, majorToMinor, MONEY_INPUT_MESSAGES, minorToMajor, moneyInputProblem, parseDecimalInput } from "../format";

type BookingRulesInput = Schema<"BookingRulesInput">;

/** The deposit of stored rules as the field shows it. */
export function depositText(rules: Pick<BookingRulesInput, "deposit_minor"> | null | undefined, currency: string): string {
  const minor = rules?.deposit_minor;
  return minor ? decimalInputValue(minorToMajor(minor, currency), currencyFractionDigits(currency)) : "";
}

/** The rules with the typed deposit, or why the deposit cannot be stored. */
export function withDeposit(
  rules: BookingRulesInput,
  text: string,
  currency: string,
): { ok: true; rules: BookingRulesInput } | { ok: false; problem: MessageKey } {
  if (text.trim() === "") {
    return { ok: true, rules: { ...rules, deposit_minor: null, deposit_currency_code: null } };
  }
  const problem = moneyInputProblem(text, currency);
  const major = problem === null ? parseDecimalInput(text, currency) : null;
  if (problem !== null || major === null) {
    return { ok: false, problem: MONEY_INPUT_MESSAGES[problem ?? "number"] };
  }
  const minor = majorToMinor(major, currency);
  return { ok: true, rules: { ...rules, deposit_minor: minor > 0 ? minor : null, deposit_currency_code: minor > 0 ? currency : null } };
}
