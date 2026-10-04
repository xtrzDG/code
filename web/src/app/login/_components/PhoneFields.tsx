"use client";

import { errorMessageKey } from "@/api/errors";
import { CountrySelect } from "@/components/CountrySelect";
import {
  Alert,
  Button,
  Field,
  Fieldset,
  Input,
  Spinner,
} from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { formatCallingCode } from "@/lib/countries";

import { DELIVERY_CHANNEL_LABELS } from "../_lib/loginTexts";
import type { Destination } from "../_lib/useDestination";

/** Country, phone number and, when several work, the channel the code comes by. */
export function PhoneFields({ destination }: { destination: Destination }) {
  const { t } = useI18n();
  const {
    countries,
    countryList,
    country,
    phoneBlock,
    isUnavailable,
    isEmailOffered,
    error,
  } = destination;

  return (
    <>
      <Field label={t("auth.country")}>
        {(control) =>
          countries.isLoading && countryList.length === 0 ? (
            <div className="flex h-9 items-center gap-2 text-sm text-ink-muted">
              <Spinner size="sm" />
              {t("common.loading")}
            </div>
          ) : (
            <CountrySelect
              {...control}
              countries={countryList}
              value={destination.countryCode}
              autoComplete="country"
              onValueChange={destination.setCountry}
            />
          )
        }
      </Field>
      {countries.error ? (
        <Alert
          tone="warning"
          action={
            <Button size="sm" variant="secondary" onClick={countries.reload}>
              {t("common.retry")}
            </Button>
          }
        >
          {t(errorMessageKey(countries.error))}
        </Alert>
      ) : null}
      <Field
        label={t("auth.phone")}
        hint={
          country
            ? t("auth.phoneHint", {
                code: formatCallingCode(country.calling_code).slice(1),
              })
            : undefined
        }
        error={error ? t(error) : undefined}
      >
        {(control) => (
          <div className="flex gap-2">
            {country ? (
              <span
                className="flex h-9 shrink-0 items-center rounded-lg border border-line bg-surface-muted px-3 text-sm text-ink-muted tabular-nums"
                aria-hidden
              >
                {formatCallingCode(country.calling_code)}
              </span>
            ) : null}
            <Input
              {...control}
              type="tel"
              inputMode="tel"
              autoComplete="tel"
              placeholder={t("auth.phonePlaceholder")}
              value={destination.phoneNumber}
              onChange={(event) =>
                destination.setPhoneNumber(event.target.value)
              }
            />
          </div>
        )}
      </Field>
      {phoneBlock !== null && !isUnavailable ? (
        <Alert tone="warning">
          <p>
            {phoneBlock === "restricted"
              ? t("loginOptions.restricted")
              : t("loginOptions.noPhoneChannels")}
          </p>
          {isEmailOffered ? (
            <Button
              variant="secondary"
              size="sm"
              className="mt-3"
              onClick={() => destination.setMethod("email")}
            >
              {t("loginOptions.useEmail")}
            </Button>
          ) : null}
        </Alert>
      ) : null}
      {phoneBlock === null && destination.phoneChannels.length > 1 ? (
        <DeliveryChannelPicker destination={destination} />
      ) : null}
    </>
  );
}

function DeliveryChannelPicker({ destination }: { destination: Destination }) {
  const { t } = useI18n();
  return (
    <Fieldset legend={t("loginOptions.channelLabel")}>
      <div className="flex flex-wrap gap-2">
        {destination.phoneChannels.map((channel) => {
          const isChosen = destination.deliveryChannel === channel;
          return (
            <label
              key={channel}
              className={cn(
                "flex h-8 cursor-pointer items-center rounded-lg border px-3 text-sm font-medium transition-colors",
                "has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-1 has-[:focus-visible]:outline-focus",
                isChosen
                  ? "border-accent bg-accent-soft text-accent-ink"
                  : "border-line text-ink-muted hover:text-ink",
              )}
            >
              <input
                type="radio"
                name="delivery-channel"
                value={channel}
                checked={isChosen}
                onChange={() => destination.setChannel(channel)}
                className="sr-only"
              />
              {t(DELIVERY_CHANNEL_LABELS[channel])}
            </label>
          );
        })}
      </div>
    </Fieldset>
  );
}
