"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { z } from "zod";

import { startLogin, verifyLogin } from "@/api/auth";
import { useCountries } from "@/api/catalog";
import { api } from "@/api/client";
import { errorMessageKey, toApiError } from "@/api/errors";
import { useApiQuery } from "@/api/hooks";
import type { OtpChallengeView, OtpDeliveryChannel } from "@/api/types";
import { CountrySelect } from "@/components/CountrySelect";
import { Alert, Button, Card, Field, Fieldset, Input, Spinner, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import { cn } from "@/lib/cn";
import {
  buildOtpStartBody,
  classifyOtpStartError,
  classifyOtpVerifyError,
  formatCallingCode,
  guessCountryCode,
  isCountryAvailable,
  looksLikeEmail,
  looksLikePhoneNumber,
  type LoginMethod,
} from "@/lib/countries";
import { messageKey } from "@/lib/validation";

import {
  chooseDeliveryChannel,
  effectiveLoginMethod,
  isEmailLoginOffered,
  isSignInUnavailable,
  phoneLoginBlock,
  withDeliveryChannel,
} from "./_lib/loginOptions";

/** The API refuses a second code for the same destination within 30 s. */
const RESEND_INTERVAL_MS = 30_000;
const CODE_LENGTH = 6;

const DELIVERY_CHANNEL_LABELS: Record<OtpDeliveryChannel, MessageKey> = {
  sms: "auth.deliveryChannels.sms",
  whatsapp: "auth.deliveryChannels.whatsapp",
  telegram: "auth.deliveryChannels.telegram",
  email: "auth.deliveryChannels.email",
};

const PROBLEM_MESSAGES = {
  countryRestricted: "auth.errors.countryRestricted",
  resendTooSoon: "auth.errors.resendTooSoon",
  cannotReceive: "auth.errors.cannotReceive",
  phoneInvalid: "auth.errors.phoneInvalid",
  emailInvalid: "auth.errors.emailInvalid",
  wrongCode: "auth.errors.wrongCode",
  tooManyAttempts: "auth.errors.tooManyAttempts",
} as const satisfies Record<string, MessageKey>;

const PhoneSchema = z
  .string()
  .trim()
  .min(1, messageKey("auth.errors.phoneRequired"))
  .refine(looksLikePhoneNumber, messageKey("auth.errors.phoneInvalid"));
const EmailSchema = z.string().trim().refine(looksLikeEmail, messageKey("auth.errors.emailInvalid"));
const CodeSchema = z.string().regex(/^\d{6}$/, messageKey("auth.errors.codeInvalid"));

interface CodeStage {
  challenge: OtpChallengeView;
  sentAt: number;
}

export function LoginScreen({ next, sessionExpired }: { next: string; sessionExpired: boolean }) {
  const { t, locale } = useI18n();
  const toast = useToast();
  const countries = useCountries();

  const [chosenMethod, setMethod] = useState<LoginMethod>("phone");
  const [chosenChannel, setChosenChannel] = useState<OtpDeliveryChannel | null>(null);
  const [chosenCountry, setChosenCountry] = useState<string | null>(null);
  const [phoneNumber, setPhoneNumber] = useState("");
  const [email, setEmail] = useState("");
  const [destinationError, setDestinationError] = useState<MessageKey | null>(null);
  const [isSending, setSending] = useState(false);

  const [codeStage, setCodeStage] = useState<CodeStage | null>(null);
  const [code, setCode] = useState("");
  const [codeError, setCodeError] = useState<MessageKey | null>(null);
  const [isVerifying, setVerifying] = useState(false);
  const [now, setNow] = useState(() => Date.now());
  const codeInputRef = useRef<HTMLInputElement>(null);

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

  // Which ways can deliver a code right now (for the chosen country). The
  // page works without it: a failed check offers everything, as before.
  const loginOptions = useApiQuery(
    () => api.GET("/v1/auth/login-options", { params: { query: countryCode ? { country_code: countryCode } : {} } }),
    [countryCode],
  );
  const options = loginOptions.data;
  const method = effectiveLoginMethod(chosenMethod, options);
  const isEmailOffered = isEmailLoginOffered(options);
  const phoneBlock = phoneLoginBlock(options);
  const phoneChannels = options?.phone_channels ?? [];
  const deliveryChannel = chooseDeliveryChannel(phoneChannels, chosenChannel);
  const isUnavailable = isSignInUnavailable(options);
  const canSend = !isUnavailable && (method === "email" || phoneBlock === null);

  const resendAt = codeStage ? codeStage.sentAt + RESEND_INTERVAL_MS : 0;
  const secondsUntilResend = Math.max(0, Math.ceil((resendAt - now) / 1000));

  useEffect(() => {
    if (!codeStage) {
      return;
    }
    codeInputRef.current?.focus();
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [codeStage]);

  async function sendCode(): Promise<boolean> {
    setSending(true);
    try {
      const challenge = await startLogin(
        withDeliveryChannel(
          buildOtpStartBody({ method, phoneNumber, email, countryCode, locale }),
          method,
          phoneChannels,
          deliveryChannel,
        ),
      );
      const sentAt = Date.now();
      setNow(sentAt);
      setCodeStage({ challenge, sentAt });
      return true;
    } catch (caught) {
      const error = toApiError(caught);
      const problem = classifyOtpStartError(error, method);
      if (problem) {
        setDestinationError(PROBLEM_MESSAGES[problem]);
        if (codeStage) {
          toast.error(error, { [error.code]: PROBLEM_MESSAGES[problem] });
        }
      } else {
        toast.error(error);
      }
      return false;
    } finally {
      setSending(false);
    }
  }

  async function onSubmitDestination(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSend) {
      return;
    }
    const parsed = (method === "phone" ? PhoneSchema : EmailSchema).safeParse(
      method === "phone" ? phoneNumber : email,
    );
    if (!parsed.success) {
      setDestinationError((parsed.error.issues[0]?.message ?? "validation.required") as MessageKey);
      return;
    }
    setDestinationError(null);
    await sendCode();
  }

  async function verify(candidate: string) {
    const parsed = CodeSchema.safeParse(candidate);
    if (!parsed.success || !codeStage) {
      setCodeError("auth.errors.codeInvalid");
      return;
    }
    setCodeError(null);
    setVerifying(true);
    try {
      await verifyLogin({ challenge_id: codeStage.challenge.challenge_id, code: parsed.data });
      // A full load picks up the account language and the new session.
      window.location.assign(next);
    } catch (caught) {
      const error = toApiError(caught);
      const problem = classifyOtpVerifyError(error);
      if (problem) {
        setCodeError(PROBLEM_MESSAGES[problem]);
      } else {
        toast.error(error);
      }
      setVerifying(false);
    }
  }

  async function resend() {
    setCode("");
    setCodeError(null);
    if (await sendCode()) {
      toast.success(t("auth.codeResent"));
    }
  }

  function changeDestination() {
    setCodeStage(null);
    setCode("");
    setCodeError(null);
  }

  if (codeStage) {
    const { challenge } = codeStage;
    return (
      <Card className="w-full max-w-md" title={t("auth.codeTitle")}>
        <form
          noValidate
          className="space-y-5"
          onSubmit={(event) => {
            event.preventDefault();
            void verify(code);
          }}
        >
          <p className="text-sm text-ink-muted">
            {t("auth.codeSentTo", {
              destination: challenge.masked_destination,
              channel: t(DELIVERY_CHANNEL_LABELS[challenge.delivery_channel]),
            })}
          </p>
          <Field
            label={t("auth.code")}
            hint={t("auth.codeHint", { minutes: Math.max(1, Math.round(challenge.expires_in_seconds / 60)) })}
            error={codeError ? t(codeError) : undefined}
          >
            {(control) => (
              <Input
                {...control}
                ref={codeInputRef}
                value={code}
                inputMode="numeric"
                autoComplete="one-time-code"
                pattern="\d{6}"
                maxLength={CODE_LENGTH}
                className="h-12 text-center font-mono text-2xl tracking-[0.5em]"
                onChange={(event) => {
                  const digits = event.target.value.replace(/\D/g, "").slice(0, CODE_LENGTH);
                  setCode(digits);
                  setCodeError(null);
                  if (digits.length === CODE_LENGTH && !isVerifying) {
                    void verify(digits);
                  }
                }}
              />
            )}
          </Field>
          <Button type="submit" fullWidth size="lg" isLoading={isVerifying} loadingText={t("auth.verifying")}>
            {t("auth.verify")}
          </Button>
          <div className="flex flex-col items-center gap-2 text-sm">
            {secondsUntilResend > 0 ? (
              <p className="text-ink-subtle" aria-live="polite">
                {t("auth.resendIn", { seconds: secondsUntilResend })}
              </p>
            ) : (
              <Button variant="ghost" size="sm" onClick={resend} isLoading={isSending} loadingText={t("auth.sendingCode")}>
                {t("auth.resend")}
              </Button>
            )}
            <Button variant="ghost" size="sm" onClick={changeDestination}>
              {t("auth.changeDestination")}
            </Button>
          </div>
        </form>
      </Card>
    );
  }

  return (
    <Card className="w-full max-w-md">
      <div className="mb-6 space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight text-ink">{t("auth.title")}</h1>
        <p className="text-sm text-ink-muted">{t("auth.subtitle")}</p>
      </div>

      {sessionExpired ? (
        <Alert tone="info" className="mb-5">
          {t("auth.sessionExpired")}
        </Alert>
      ) : null}

      {isUnavailable ? (
        <Alert tone="warning" className="mb-5">
          {t("loginOptions.nothingAvailable")}
        </Alert>
      ) : null}

      <form noValidate className="space-y-5" onSubmit={onSubmitDestination}>
        <fieldset hidden={!isEmailOffered}>
          <legend className="sr-only">{t("auth.methodLabel")}</legend>
          <div className="grid grid-cols-2 gap-1 rounded-xl bg-surface-muted p-1">
            {(["phone", "email"] as const).map((option) => (
              <label
                key={option}
                className={cn(
                  "flex cursor-pointer items-center justify-center rounded-lg px-3 py-2 text-sm font-medium transition-colors has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-focus",
                  method === option ? "bg-surface text-ink shadow-sm" : "text-ink-muted hover:text-ink",
                )}
              >
                <input
                  type="radio"
                  name="method"
                  value={option}
                  checked={method === option}
                  onChange={() => {
                    setMethod(option);
                    setDestinationError(null);
                  }}
                  className="sr-only"
                />
                {option === "phone" ? t("auth.methodPhone") : t("auth.methodEmail")}
              </label>
            ))}
          </div>
        </fieldset>

        {method === "phone" ? (
          <>
            <Field label={t("auth.country")}>
              {(control) =>
                countries.isLoading && countryList.length === 0 ? (
                  <div className="flex h-10 items-center gap-2 text-sm text-ink-muted">
                    <Spinner size="sm" />
                    {t("common.loading")}
                  </div>
                ) : (
                  <CountrySelect
                    {...control}
                    countries={countryList}
                    value={countryCode}
                    autoComplete="country"
                    onValueChange={(value) => {
                      setChosenCountry(value);
                      setDestinationError(null);
                    }}
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
              hint={country ? t("auth.phoneHint", { code: formatCallingCode(country.calling_code).slice(1) }) : undefined}
              error={destinationError ? t(destinationError) : undefined}
            >
              {(control) => (
                <div className="flex gap-2">
                  {country ? (
                    <span
                      className="flex h-10 shrink-0 items-center rounded-lg border border-line bg-surface-muted px-3 text-sm text-ink-muted"
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
                    value={phoneNumber}
                    onChange={(event) => {
                      setPhoneNumber(event.target.value);
                      setDestinationError(null);
                    }}
                  />
                </div>
              )}
            </Field>
            {phoneBlock !== null && !isUnavailable ? (
              <Alert tone="warning">
                <p>{phoneBlock === "restricted" ? t("loginOptions.restricted") : t("loginOptions.noPhoneChannels")}</p>
                {isEmailOffered ? (
                  <Button
                    variant="secondary"
                    size="sm"
                    className="mt-3"
                    onClick={() => {
                      setMethod("email");
                      setDestinationError(null);
                    }}
                  >
                    {t("loginOptions.useEmail")}
                  </Button>
                ) : null}
              </Alert>
            ) : null}
            {phoneBlock === null && phoneChannels.length > 1 ? (
              <Fieldset legend={t("loginOptions.channelLabel")}>
                <div className="flex flex-wrap gap-2">
                  {phoneChannels.map((channel) => (
                    <label
                      key={channel}
                      className={cn(
                        "flex cursor-pointer items-center rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-focus",
                        deliveryChannel === channel
                          ? "border-accent bg-accent-soft text-accent"
                          : "border-line text-ink-muted hover:text-ink",
                      )}
                    >
                      <input
                        type="radio"
                        name="delivery-channel"
                        value={channel}
                        checked={deliveryChannel === channel}
                        onChange={() => setChosenChannel(channel)}
                        className="sr-only"
                      />
                      {t(DELIVERY_CHANNEL_LABELS[channel])}
                    </label>
                  ))}
                </div>
              </Fieldset>
            ) : null}
          </>
        ) : (
          <Field label={t("auth.email")} error={destinationError ? t(destinationError) : undefined}>
            {(control) => (
              <Input
                {...control}
                type="email"
                inputMode="email"
                autoComplete="email"
                placeholder={t("auth.emailPlaceholder")}
                value={email}
                onChange={(event) => {
                  setEmail(event.target.value);
                  setDestinationError(null);
                }}
              />
            )}
          </Field>
        )}

        <Button
          type="submit"
          fullWidth
          size="lg"
          isLoading={isSending}
          loadingText={t("auth.sendingCode")}
          disabled={!canSend}
        >
          {t("auth.sendCode")}
        </Button>
      </form>
    </Card>
  );
}
