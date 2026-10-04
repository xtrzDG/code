"use client";

/**
 * Setting up an authenticator app: install one, scan the QR code (or type
 * the key), then enter its first code. Used at an admin's first sign-in
 * and in Account → Security; the caller turns the code into the request.
 */

import { useState, type FormEvent } from "react";

import type { TotpEnrollmentView } from "@/api/types";
import { CopyButton } from "@/components/workspace/CopyButton";
import { Button } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { groupedKey, isCompleteOneTimeCode } from "@/lib/security/secondFactor";

import { OneTimeCodeField } from "./OneTimeCodeField";
import { TotpQrCode } from "./TotpQrCode";

export function AuthenticatorSetup({
  enrollment,
  onConfirm,
  isConfirming,
  error,
}: {
  enrollment: TotpEnrollmentView;
  onConfirm: (code: string) => void;
  isConfirming: boolean;
  /** A localized problem with the last code. */
  error?: string;
}) {
  const { t } = useI18n();
  const [code, setCode] = useState("");
  const [formatError, setFormatError] = useState(false);

  const submit = (candidate: string) => {
    if (!isCompleteOneTimeCode(candidate)) {
      setFormatError(true);
      return;
    }
    setFormatError(false);
    onConfirm(candidate);
  };

  return (
    <form
      noValidate
      className="space-y-5"
      onSubmit={(event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        submit(code);
      }}
    >
      <ol className="list-decimal space-y-1.5 ps-5 text-sm text-ink-muted marker:text-ink-subtle">
        <li>{t("mfa.setup.stepInstall")}</li>
        <li>{t("mfa.setup.stepScan")}</li>
        <li>{t("mfa.setup.stepCode")}</li>
      </ol>
      {/* Side by side where the container is wide (a dialog), stacked in the narrow sign-in card. */}
      <div className="@container">
        <div className="flex flex-col items-center gap-4 @md:flex-row @md:items-start">
          <TotpQrCode
            uri={enrollment.provisioning_uri}
            label={t("mfa.setup.qrLabel")}
          />
          <div className="flex w-full min-w-0 flex-col items-center gap-2 text-center @md:items-start @md:text-start">
            <p className="text-xs font-medium tracking-wide text-ink-subtle uppercase">
              {t("mfa.setup.key")}
            </p>
            <p className="font-mono text-sm break-all text-ink" translate="no">
              {groupedKey(enrollment.secret)}
            </p>
            <p
              className="max-w-full truncate text-xs text-ink-subtle"
              title={enrollment.account_label}
            >
              {enrollment.issuer} · {enrollment.account_label}
            </p>
            <CopyButton
              value={enrollment.secret}
              label={t("mfa.setup.copyKey")}
            />
          </div>
        </div>
      </div>
      <OneTimeCodeField
        label={t("mfa.setup.code")}
        value={code}
        error={formatError ? t("mfa.errors.codeFormat") : error}
        onChange={(digits) => {
          setCode(digits);
          setFormatError(false);
        }}
        onComplete={(digits) => {
          if (!isConfirming) {
            submit(digits);
          }
        }}
      />
      <Button
        type="submit"
        fullWidth
        isLoading={isConfirming}
        loadingText={t("mfa.setup.confirming")}
      >
        {t("mfa.setup.confirm")}
      </Button>
    </form>
  );
}
