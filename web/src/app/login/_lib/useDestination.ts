"use client";

/**
 * Where the sign-in code goes: phone (country, number, delivery channel) or
 * e-mail, and which of them work right now for the chosen country
 * (GET /v1/auth/login-options; a failed check offers everything).
 */

import { useState } from "react";

import { useCountries } from "@/api/catalog";
import { api } from "@/api/client";
import { useApiQuery } from "@/api/hooks";
import type { OtpDeliveryChannel } from "@/api/types";
import type { MessageKey } from "@/i18n/translate";
import { guessCountryCode, isCountryAvailable, type LoginMethod } from "@/lib/countries";

import {
  chooseDeliveryChannel,
  effectiveLoginMethod,
  isEmailLoginOffered,
  isSignInUnavailable,
  phoneLoginBlock,
} from "./loginOptions";

export function useDestination() {
  const countries = useCountries();
  const [chosenMethod, setChosenMethod] = useState<LoginMethod>("phone");
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

  const loginOptions = useApiQuery(
    () => api.GET("/v1/auth/login-options", { params: { query: countryCode ? { country_code: countryCode } : {} } }),
    [countryCode],
  );
  const options = loginOptions.data;
  const method = effectiveLoginMethod(chosenMethod, options);
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
    canSend: !isUnavailable && (method === "email" || phoneBlock === null),
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
    setPhoneNumber: (value: string) => {
      setPhoneNumber(value);
      setError(null);
    },
    setEmail: (value: string) => {
      setEmail(value);
      setError(null);
    },
  };
}

export type Destination = ReturnType<typeof useDestination>;
