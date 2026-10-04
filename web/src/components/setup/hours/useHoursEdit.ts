"use client";

/**
 * "Hours and bookings" in the edit mode, as state. The week and the
 * booking rules save themselves as the owner changes them. When the
 * business has not saved them yet, the niche's usual ones are shown as a
 * suggestion: saved only once the owner changes something or accepts
 * them as they are, never by themselves.
 */

import { useEffect, useState } from "react";

import { bookingForm, bookingRulesInput, type BookingForm } from "@/lib/tunnel/bookings";
import { depositText, withDeposit } from "@/lib/profile/deposit";

import { useProfileField } from "../edit/useProfileField";
import type { StepContext } from "../flow/stepContext";
import { hoursToRows, rowsToHours, type DayRows } from "./HoursEditor";

export function useHoursEdit(ctx: StepContext) {
  const { wizard, starters } = ctx;
  const currency = wizard.currency_code;
  const takesBookings = wizard.niche.takes_bookings;
  const savedHours = wizard.profile.hours ?? [];
  const savedRules = wizard.profile.booking_rules ?? null;

  const [days, setDays] = useState<DayRows[]>(() => hoursToRows(savedHours.length > 0 ? savedHours : (starters.hours ?? [])));
  // The week on screen is the owner's: saved before, changed or accepted here.
  const [hoursTaken, setHoursTaken] = useState(() => savedHours.length > 0 || (starters.hours ?? []).length === 0);
  const [booking, setBooking] = useState<BookingForm>(() => bookingForm(savedRules, starters.booking_rules));
  const [deposit, setDeposit] = useState(() => depositText(savedRules, currency));
  const [rulesTaken, setRulesTaken] = useState(() => savedRules !== null || !starters.booking_rules);
  const [accepted, setAccepted] = useState(0);

  const hours = rowsToHours(days);
  const week = hours.ok && hours.hours.length > 0 ? hours.hours : null;
  const hoursSave = useProfileField(ctx.businessId, hoursTaken ? week : null, (value) => ({ hours: value ?? [] }), { isValid: (value) => value !== null });

  const rules = bookingRulesInput(booking, savedRules ?? starters.booking_rules);
  const withMoney = rules.ok ? withDeposit(rules.rules, deposit, currency) : null;
  const ruleValue = takesBookings && rulesTaken && withMoney?.ok ? withMoney.rules : null;
  const rulesSave = useProfileField(ctx.businessId, ruleValue, (value) => ({ booking_rules: value }), { isValid: (value) => value !== null });

  // A suggestion accepted as it is goes at once, not after the typing pause.
  const { flush: flushHours } = hoursSave;
  const { flush: flushRules } = rulesSave;
  useEffect(() => {
    if (accepted > 0) {
      void flushHours();
      void flushRules();
    }
  }, [accepted, flushHours, flushRules]);

  return {
    takesBookings,
    bySlots: wizard.niche.booking_unit !== "night",
    days,
    setDays: (next: DayRows[]) => {
      setDays(next);
      setHoursTaken(true);
    },
    isHoursSuggested: !hoursTaken,
    acceptHours: () => {
      setHoursTaken(true);
      setAccepted((count) => count + 1);
    },
    hourErrors: hours.ok ? {} : hours.errors,
    noHours: hours.ok && hours.hours.length === 0,
    hoursError: hoursSave.error,
    booking,
    setBooking: (next: BookingForm) => {
      setBooking(next);
      setRulesTaken(true);
    },
    deposit,
    setDeposit: (next: string) => {
      setDeposit(next);
      setRulesTaken(true);
    },
    isRulesSuggested: takesBookings && !rulesTaken,
    acceptRules: () => {
      setRulesTaken(true);
      setAccepted((count) => count + 1);
    },
    bookingProblem: rules.ok ? null : rules.problem,
    depositProblem: withMoney && !withMoney.ok ? withMoney.problem : null,
    rulesError: rulesSave.error,
  };
}

export type HoursEditState = ReturnType<typeof useHoursEdit>;
