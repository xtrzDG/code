"use client";

/**
 * The two steps of signing in: send a code to the destination, then check
 * the code (with resend and "send by another channel" on the way). A
 * successful check loads `next` in full, which picks up the session and the
 * account's language.
 */

import { useEffect, useRef, useState, type FormEvent } from "react";

import { startLogin, verifyLogin } from "@/api/auth";
import { toApiError } from "@/api/errors";
import type { OtpChallengeView, OtpDeliveryChannel } from "@/api/types";
import { useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import { buildOtpStartBody, classifyOtpStartError, classifyOtpVerifyError } from "@/lib/countries";

import { findBotCheckSiteKey } from "./botCheck";
import { withDeliveryChannel } from "./loginOptions";
import { CodeSchema, EmailSchema, PROBLEM_MESSAGES, PhoneSchema, RESEND_INTERVAL_MS } from "./loginTexts";
import { useDestination } from "./useDestination";

interface CodeStage {
  challenge: OtpChallengeView;
  sentAt: number;
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
  const [now, setNow] = useState(() => Date.now());
  const codeInputRef = useRef<HTMLInputElement>(null);

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
      setCodeStage({ challenge, sentAt });
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
    changeDestination: () => {
      setCodeStage(null);
      setBotCheck(null);
      clearCode();
    },
  };
}

export type LoginFlow = ReturnType<typeof useLoginFlow>;
