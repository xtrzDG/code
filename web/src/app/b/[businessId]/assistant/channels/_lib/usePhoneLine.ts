"use client";

/**
 * The phone line of a business: the number it rents from the platform, an
 * open request to the team, where numbers are self-serve; and the owner's
 * actions (search, take a number, ask the team, cancel the request).
 * Taking a number connects the phone channel, so the channels and the
 * assistant's readiness are reloaded when next shown.
 */

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";
import { useI18n } from "@/i18n/client";

import { PHONE_NUMBER_REFUSALS, type PhoneNumberRequestBody, type PhoneNumberType, type RentPhoneNumberBody } from "./phoneLine";

export interface PhoneNumberSearch {
  countryCode: string;
  numberType: PhoneNumberType;
  city?: string;
}

export function usePhoneLine(businessId: string) {
  const { locale } = useI18n();
  return useQuery(queryKeys.channels.phoneLine(businessId, locale), () =>
    api.GET("/v1/businesses/{business_id}/phone-line", {
      params: { path: { business_id: businessId }, query: { language: locale } },
    }),
  );
}

export function usePhoneLineActions(businessId: string) {
  const { locale } = useI18n();
  const path = { business_id: businessId };
  const lineKey = queryKeys.channels.phoneLine(businessId, locale);
  const connected = [queryKeys.channels.all(businessId), queryKeys.assistant.all(businessId)];

  const search = useMutation(
    (query: PhoneNumberSearch) =>
      api.GET("/v1/businesses/{business_id}/phone-line/offers", {
        params: {
          path,
          query: { country: query.countryCode, number_type: query.numberType, city: query.city, language: locale },
        },
      }),
    { errorToast: false },
  );
  const rent = useMutation(
    (body: RentPhoneNumberBody) =>
      api.POST("/v1/businesses/{business_id}/phone-line/number", { params: { path, query: { language: locale } }, body }),
    { errorToast: false, reasonMessages: PHONE_NUMBER_REFUSALS, invalidate: [lineKey], stale: connected },
  );
  const ask = useMutation(
    (body: PhoneNumberRequestBody) => api.POST("/v1/businesses/{business_id}/phone-line/request", { params: { path }, body }),
    { errorToast: false, invalidate: [lineKey] },
  );
  const cancel = useMutation(
    () => api.DELETE("/v1/businesses/{business_id}/phone-line/request", { params: { path } }),
    { invalidate: [lineKey] },
  );
  return { search, rent, ask, cancel };
}
