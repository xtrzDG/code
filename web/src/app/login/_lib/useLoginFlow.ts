"use client";

/**
 * The two steps of signing in: send a code to the destination, then check
 * the code (with resend and "send by another channel" on the way). A
 * successful check (or its second step, SecondStepForm) loads `next` in
 * full, which picks up the session and the
 * account's language.
 */

import { useEffect, useRef, useState, type FormEvent } from "react";

import { needsSecondStep, startLogin, verifyLogin, type SecondStepRequired } from "@/api/auth";
import { toApiError } from "@/api/errors";
import type { OtpChallengeView, OtpDeliveryChannel } from "@/api/types";
import { useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import { buildOtpStartBody, classifyOtpStartError, classifyOtpVerifyError } from "@/lib/countries";

import { findBotCheckSiteKey } from "./botCheck";
import { acceptedTermsBody, preferConsentVersions, type ConsentVersions } from "./legalConsent";
import { withDeliveryChannel } from "./loginOptions";
import { CodeSchema, EmailSchema, PROBLEM_MESSAGES, PhoneSchema, RESEND_INTERVAL_MS } from "./loginTexts";
import { useDestination } from "./useDestination";

interface CodeStage {
  challenge: OtpChallengeView;
  sentAt: number;
  /** The documents the code step names, kept from the moment the code was sent. */
  consent: ConsentVersions;
}

/** The API asked for a bot check before sending; `attempt` remounts the widget. */
interface BotCheckStage {
  siteKey: string;
  channel: OtpDeliveryChannel | undefined;
  isRetry: boolean;
  attempt: number;
}

export function useLoginFlow(next: string) {
  const { t, locale } = useI18n();
  const toast = useToast();
  const destination = useDestination();
  const [isSending, setSending] = useState(false);
  const [botCheck, setBotCheck] = useState<BotCheckStage | null>(null);

  const [codeStage, setCodeStage] = useState<CodeStage | null>(null);
  const [code, setCode] = useState("");
  const [codeError, setCodeError] = useState<MessageKey | null>(null);
  const [isVerifying, setVerifying] = useState(false);
  /** The code was right; the account asks for its authenticator (or to set one up). */
  const [secondStep, setSecondStep] = useState<SecondStepRequired | null>(null);
  const [now, setNow] = useState(() => Date.now());
  const codeInputRef = useRef<HTMLInputElement>(null);

  const resendAt = codeStage ? codeStage.sentAt + RESEND_INTERVAL_MS : 0;
  const secondsUntilResend = Math.max(0, Math.ceil((resendAt - now) / 1000));

  // The versions named when the code was sent; versions that arrive later
  // only fill in what the step did not know yet.
  const consent = codeStage
    ? preferConsentVersions(codeStage.consent, {
        termsVersion: destination.termsVersion,
        privacyVersion: destination.privacyVersion,
      })
    : null;

  // Each code sent focuses the code field and starts the resend countdown.
  const sentAt = codeStage?.sentAt;
  useEffect(() => {
    if (sentAt === undefined) {
      return;
    }
    codeInputRef.current?.focus();
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [sentAt]);

  async function sendCode(channelOverride?: OtpDeliveryChannel, turnstileToken?: string): Promise<boolean> {
    const { method, phoneNumber, email, countryCode, phoneChannels, deliveryChannel } = destination;
    setSending(true);
    try {
      const challenge = await startLogin({
        ...withDeliveryChannel(
          buildOtpStartBody({ method, phoneNumber, email, countryCode, locale }),
          method,
          phoneChannels,
          channelOverride ?? deliveryChannel,
        ),
        ...(turnstileToken ? { turnstile_token: turnstileToken } : {}),
      });
      const sentAt = Date.now();
      setBotCheck(null);
      setNow(sentAt);
      const current = { termsVersion: destination.termsVersion, privacyVersion: destination.privacyVersion };
      setCodeStage((previous) => ({
        challenge,
        sentAt,
        consent: preferConsentVersions(current, previous?.consent ?? null),
      }));
      return true;
    } catch (caught) {
      const error = toApiError(caught);
      const siteKey = findBotCheckSiteKey(error);
      if (siteKey) {
        // A risky request: the code goes out once the visitor passes the check.
        setBotCheck((previous) => ({
          siteKey,
          channel: channelOverride,
          isRetry: turnstileToken !== undefined,
          attempt: (previous?.attempt ?? 0) + 1,
        }));
        return false;
      }
      const problem = classifyOtpStartError(error, method);
      if (problem) {
        destination.setError(PROBLEM_MESSAGES[problem]);
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

  async function submitDestination(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!destination.canSend) {
      return;
    }
    const isPhone = destination.method === "phone";
    const parsed = (isPhone ? PhoneSchema : EmailSchema).safeParse(isPhone ? destination.phoneNumber : destination.email);
    if (!parsed.success) {
      destination.setError((parsed.error.issues[0]?.message ?? "validation.required") as MessageKey);
      return;
    }
    destination.setError(null);
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
      const answer = await verifyLogin({
        challenge_id: codeStage.challenge.challenge_id,
        code: parsed.data,
        ...acceptedTermsBody(consent?.termsVersion ?? null),
      });
      if (needsSecondStep(answer)) {
        setSecondStep(answer);
        setVerifying(false);
        return;
      }
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

  /** The check passed: ask for the code again with its one-time token. */
  async function passBotCheck(token: string) {
    const isResend = codeStage !== null;
    if ((await sendCode(botCheck?.channel, token)) && isResend) {
      toast.success(t("auth.codeResent"));
    }
  }

  function clearCode() {
    setCode("");
    setCodeError(null);
  }

  async function resend() {
    clearCode();
    if (await sendCode()) {
      toast.success(t("auth.codeResent"));
    }
  }

  /**
   * The code went by a channel the number may not use (a number without
   * WhatsApp gets nothing, and WhatsApp reports that only later): the API
   * lets the visitor switch channel at once, without the resend wait.
   */
  async function sendByOtherChannel(channel: OtpDeliveryChannel) {
    destination.setChannel(channel);
    clearCode();
    if (await sendCode(channel)) {
      toast.success(t("auth.codeResent"));
    }
  }

  return {
    destination,
    isSending,
    submitDestination,
    botCheck,
    passBotCheck,
    challenge: codeStage?.challenge ?? null,
    /** The terms and privacy policy the code step's acceptance line names. */
    consent,
    code,
    codeError,
    isVerifying,
    secondsUntilResend,
    codeInputRef,
    typeCode: (digits: string) => {
      setCode(digits);
      setCodeError(null);
    },
    verify,
    resend,
    sendByOtherChannel,
    secondStep,
    destinationLabel: destination.method === "phone" ? destination.phoneNumber : destination.email,
    changeDestination: () => {
      setSecondStep(null);
      setCodeStage(null);
      setBotCheck(null);
      clearCode();
    },
  };
}

export type LoginFlow = ReturnType<typeof useLoginFlow>;
