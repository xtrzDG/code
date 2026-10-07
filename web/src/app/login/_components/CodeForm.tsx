"use client";

import type { OtpChallengeView } from "@/api/types";
import { Button, Field, Input } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { toAsciiDigits } from "@/lib/countries";

import { otherDeliveryChannels } from "../_lib/loginOptions";
import { CODE_LENGTH, DELIVERY_CHANNEL_LABELS } from "../_lib/loginTexts";
import type { LoginFlow } from "../_lib/useLoginFlow";
import { TermsLine } from "./TermsLine";

/** Step two: the 6-digit code, checked as soon as the last digit is typed. */
export function CodeForm({ flow, challenge }: { flow: LoginFlow; challenge: OtpChallengeView }) {
  const { t } = useI18n();
  const { code, codeError, isVerifying, isSending, secondsUntilResend } = flow;
  const otherChannels =
    challenge.login_method === "phone"
      ? otherDeliveryChannels(flow.destination.phoneChannels, challenge.delivery_channel)
      : [];

  return (
    <form
      noValidate
      className="space-y-5"
      onSubmit={(event) => {
        event.preventDefault();
        void flow.verify(code);
      }}
    >
      <div className="space-y-1.5">
        <h1 className="text-xl font-semibold tracking-tight text-ink">{t("auth.codeTitle")}</h1>
        <p className="text-sm text-ink-muted">
          {t(`auth.codeSentTo.${challenge.delivery_channel}`, { destination: challenge.masked_destination })}
        </p>
      </div>
      <Field
        label={t("auth.code")}
        hint={t("auth.codeHint", { minutes: Math.max(1, Math.round(challenge.expires_in_seconds / 60)) })}
        error={codeError ? t(codeError) : undefined}
      >
        {(control) => (
          <Input
            {...control}
            ref={flow.codeInputRef}
            value={code}
            inputMode="numeric"
            autoComplete="one-time-code"
            pattern="\d{6}"
            maxLength={CODE_LENGTH}
            className="h-12 text-center font-mono text-2xl tracking-[0.5em]"
            onChange={(event) => {
              // Codes typed with an Arabic, Persian or full-width keyboard count too.
              const digits = toAsciiDigits(event.target.value).replace(/\D/g, "").slice(0, CODE_LENGTH);
              flow.typeCode(digits);
              if (digits.length === CODE_LENGTH && !isVerifying) {
                void flow.verify(digits);
              }
            }}
          />
        )}
      </Field>
      <Button type="submit" fullWidth size="lg" isLoading={isVerifying} loadingText={t("auth.verifying")}>
        {t("auth.verify")}
      </Button>
      {flow.consent?.termsVersion ? (
        <TermsLine termsVersion={flow.consent.termsVersion} privacyVersion={flow.consent.privacyVersion} />
      ) : null}
      <div className="flex flex-col items-center gap-1 border-t border-line pt-4 text-sm">
        {secondsUntilResend > 0 ? (
          <p className="py-1.5 text-ink-subtle" aria-live="polite">
            {t("auth.resendIn", { seconds: secondsUntilResend })}
          </p>
        ) : (
          <Button variant="ghost" size="sm" onClick={flow.resend} isLoading={isSending} loadingText={t("auth.sendingCode")}>
            {t("auth.resend")}
          </Button>
        )}
        {otherChannels.map((channel) => (
          <Button
            key={channel}
            variant="ghost"
            size="sm"
            onClick={() => void flow.sendByOtherChannel(channel)}
            disabled={isSending}
          >
            {t("auth.sendByChannelInstead", { channel: t(DELIVERY_CHANNEL_LABELS[channel]) })}
          </Button>
        ))}
        <Button variant="ghost" size="sm" onClick={flow.changeDestination}>
          {t("auth.changeDestination")}
        </Button>
      </div>
    </form>
  );
}
