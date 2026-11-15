"use client";

/**
 * Where the sign-in code goes: phone (country, number, delivery channel) or
 * e-mail, and which of them work right now for the chosen country
 * (GET /v1/auth/login-options; a failed check offers everything). The
 * method starts as the one of the page's first HTML (openingMethod.ts) and
 * changes only when the visitor changes it. An answer that arrives later
 * and says that the method shown cannot deliver leaves its form in place:
 * the form explains, offers the other method and cannot send.
 */

import { useState } from "react";

import { useCountries } from "@/api/catalog";
import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useQuery } from "@/api/useQuery";
import type { OtpDeliveryChannel } from "@/api/types";
import type { MessageKey } from "@/i18n/translate";
import { guessCountryCode, isCountryAvailable, type LoginMethod } from "@/lib/countries";
import { splitInternationalNumber } from "@/lib/internationalNumber";

import {
  canSendLoginCode,
  chooseDeliveryChannel,
  isEmailLoginOffered,
  isSignInUnavailable,
  phoneLoginBlock,
} from "./loginOptions";

export function useDestination(openingMethod: LoginMethod) {
  const countries = useCountries();
  const [method, setChosenMethod] = useState<LoginMethod>(openingMethod);
  const [chosenChannel, setChosenChannel] = useState<OtpDeliveryChannel | null>(null);
  const [chosenCountry, setChosenCountry] = useState<string | null>(null);
  const [phoneNumber, setPhoneNumber] = useState("");
  const [email, setEmail] = useState("");
  const [error, setError] = useState<MessageKey | null>(null);

  const countryList = countries.data?.countries ?? [];
  const guessedCountry =
    countryList.length > 0 && typeof navigator !== "undefined"
      ? guessCountryCode(
          navigator.languages ?? [navigator.language],
          countryList.filter(isCountryAvailable).map((country) => country.country_code),
        )
      : null;
  const countryCode = chosenCountry ?? guessedCountry;
  const country = countryList.find((item) => item.country_code === countryCode);

  const loginOptions = useQuery(queryKeys.auth.loginOptions(countryCode ?? null), () =>
    api.GET("/v1/auth/login-options", { params: { query: countryCode ? { country_code: countryCode } : {} } }),
  );
  const options = loginOptions.data;
  const phoneBlock = phoneLoginBlock(options);
  const phoneChannels = options?.phone_channels ?? [];
  const isUnavailable = isSignInUnavailable(options);

  return {
    countries,
    countryList,
    countryCode,
    country,
    method,
    isEmailOffered: isEmailLoginOffered(options),
    phoneBlock,
    phoneChannels,
    deliveryChannel: chooseDeliveryChannel(phoneChannels, chosenChannel),
    isUnavailable,
    /** The terms and privacy policy the code step's acceptance line names. */
    termsVersion: options?.terms_version ?? null,
    privacyVersion: options?.privacy_version ?? null,
    canSend: canSendLoginCode(method, options),
    phoneNumber,
    email,
    error,
    setError,
    setChannel: setChosenChannel,
    /** Each change clears the error shown under the field. */
    setMethod: (value: LoginMethod) => {
      setChosenMethod(value);
      setError(null);
    },
    setCountry: (value: string | null) => {
      setChosenCountry(value);
      setError(null);
    },
    /** A number typed or autofilled with its code ("+39 351…") moves the code into the country picker. */
    setPhoneNumber: (value: string) => {
      const international = splitInternationalNumber(value, countryList, countryCode ?? null);
      if (international) {
        setChosenCountry(international.countryCode);
      }
      setPhoneNumber(international ? international.nationalNumber : value);
      setError(null);
    },
    setEmail: (value: string) => {
      setEmail(value);
      setError(null);
    },
  };
}

export type Destination = ReturnType<typeof useDestination>;
