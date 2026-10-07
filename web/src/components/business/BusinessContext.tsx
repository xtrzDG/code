"use client";

/**
 * The open business and the signed-in user, loaded once by
 * app/b/[businessId]/layout.tsx and available to every business page:
 *
 *     const { business, me, isOwner } = useBusiness();
 *     const format = useBusinessFormat();
 *     format.dateTime(booking.starts_at);   // business time zone, UI language
 *     format.money(item.price_minor);       // business currency
 */

import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

import type { BusinessView, CurrentUserView } from "@/api/types";
import { useI18n } from "@/i18n/client";
import {
  formatDate,
  formatDateTime,
  formatMoney,
  formatNumber,
  formatTime,
  type Timestamp,
} from "@/lib/format";

export interface BusinessContextValue {
  business: BusinessView;
  me: CurrentUserView;
  isOwner: boolean;
  isPlatformAdmin: boolean;
  /** The assistant exists (the business left "onboarding"): the cabinet's sections open. */
  isSetUp: boolean;
  /** The first version was just built: open the sections now, before the refreshed business arrives. */
  markSetUp: () => void;
}

const BusinessContext = createContext<BusinessContextValue | null>(null);

export function BusinessProvider({
  business,
  me,
  children,
}: {
  business: BusinessView;
  me: CurrentUserView;
  children: ReactNode;
}) {
  const [isBuiltHere, setBuiltHere] = useState(false);
  const value = useMemo<BusinessContextValue>(
    () => ({
      business,
      me,
      isOwner: business.viewer_role === "owner",
      isPlatformAdmin: me.user.is_platform_admin,
      isSetUp: business.status !== "onboarding" || isBuiltHere,
      markSetUp: () => setBuiltHere(true),
    }),
    [business, me, isBuiltHere],
  );
  return <BusinessContext.Provider value={value}>{children}</BusinessContext.Provider>;
}

export function useBusiness(): BusinessContextValue {
  const value = useContext(BusinessContext);
  if (!value) {
    throw new Error("useBusiness() must be used inside app/b/[businessId] pages.");
  }
  return value;
}

/** The business of the page, or null outside app/b/[businessId] (the account menu on other pages). */
export function useOptionalBusiness(): BusinessContextValue | null {
  return useContext(BusinessContext);
}

export interface BusinessFormat {
  dateTime: (value: Timestamp) => string;
  date: (value: Timestamp) => string;
  time: (value: Timestamp) => string;
  /** Minor units in the business currency (or another `currency`). */
  money: (minor: number, currency?: string) => string;
  number: (value: number) => string;
  timeZone: string;
  currency: string;
}

/** Formatters bound to the business time zone and currency and the UI language. */
export function useBusinessFormat(): BusinessFormat {
  const { business } = useBusiness();
  const { locale } = useI18n();
  return useMemo(() => {
    const timeZone = business.timezone;
    return {
      dateTime: (value) => formatDateTime(value, { locale, timeZone }),
      date: (value) => formatDate(value, { locale, timeZone }),
      time: (value) => formatTime(value, { locale, timeZone }),
      money: (minor, currency) => formatMoney(minor, currency ?? business.currency_code, locale),
      number: (value) => formatNumber(value, locale),
      timeZone,
      currency: business.currency_code,
    };
  }, [business.timezone, business.currency_code, locale]);
}
