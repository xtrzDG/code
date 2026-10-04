"use client";

import type { SecondStepRequired } from "@/api/auth";
import { AuthenticatorSetup } from "@/components/security/AuthenticatorSetup";
import { OneTimeCodeField } from "@/components/security/OneTimeCodeField";
import { RecoveryCodesPanel } from "@/components/security/RecoveryCodesPanel";
import { Button, Field, Input } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { RECOVERY_CODE_EXAMPLE } from "@/lib/security/secondFactor";

import { useSecondStep } from "../_lib/useSecondStep";

function Heading({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="space-y-1.5">
      <h1 className="text-xl font-semibold tracking-tight text-ink">{title}</h1>
      <p className="text-sm text-ink-muted">{description}</p>
    </div>
  );
}

/**
 * Step three for people with an authenticator app (and every platform
 * admin): its code, or a recovery code; an admin without an app sets one
 * up here and saves the recovery codes.
 */
export function SecondStepForm({
  step,
  next,
  account,
  onStartOver,
}: {
  step: SecondStepRequired;
  next: string;
  account: string;
  onStartOver: () => void;
}) {
  const { t } = useI18n();
  const flow = useSecondStep(step, next);

  if (flow.newCodes) {
    return (
      <div className="space-y-5">
        <Heading
          title={t("mfa.recovery.title")}
          description={t("security.app.turnedOn")}
        />
        <RecoveryCodesPanel
          codes={flow.newCodes}
          account={account}
          onDone={flow.finish}
        />
      </div>
    );
  }

  if (flow.requiresEnrollment) {
    return (
      <div className="space-y-5">
        <Heading
          title={t("mfa.enrollment.title")}
          description={t("mfa.enrollment.description")}
        />
        {flow.enrollment ? (
          <AuthenticatorSetup
            enrollment={flow.enrollment}
            onConfirm={flow.confirmSetup}
            isConfirming={flow.isChecking}
            error={flow.problem ?? undefined}
          />
        ) : (
          <Button
            fullWidth
            size="lg"
            isLoading={flow.isStartingSetup}
            loadingText={t("mfa.enrollment.starting")}
            onClick={() => void flow.startSetup()}
          >
            {t("mfa.enrollment.start")}
          </Button>
        )}
        {flow.problem && !flow.enrollment ? (
          <p className="text-sm text-danger">{flow.problem}</p>
        ) : null}
        <div className="border-t border-line pt-4 text-center">
          <Button variant="ghost" size="sm" onClick={onStartOver}>
            {t("mfa.secondStep.startOver")}
          </Button>
        </div>
      </div>
    );
  }

  return (
    <form
      noValidate
      className="space-y-5"
      onSubmit={(event) => {
        event.preventDefault();
        void flow.submit();
      }}
    >
      <Heading
        title={t("mfa.secondStep.title")}
        description={
          flow.useRecovery
            ? t("mfa.secondStep.recoveryDescription")
            : t("mfa.secondStep.description")
        }
      />
      {flow.useRecovery ? (
        <Field
          label={t("mfa.secondStep.recoveryCode")}
          hint={t("mfa.secondStep.recoveryHint", {
            example: RECOVERY_CODE_EXAMPLE,
          })}
          error={flow.problem ?? undefined}
        >
          {(control) => (
            <Input
              {...control}
              value={flow.recoveryCode}
              autoComplete="off"
              autoCapitalize="none"
              spellCheck={false}
              onChange={(event) => flow.setRecoveryCode(event.target.value)}
            />
          )}
        </Field>
      ) : (
        <OneTimeCodeField
          label={t("mfa.secondStep.code")}
          value={flow.code}
          error={flow.problem ?? undefined}
          onChange={flow.typeCode}
          onComplete={(digits) => void flow.submit(digits)}
        />
      )}
      <Button
        type="submit"
        fullWidth
        size="lg"
        isLoading={flow.isChecking}
        loadingText={t("mfa.secondStep.verifying")}
      >
        {t("mfa.secondStep.verify")}
      </Button>
      <div className="flex flex-col items-center gap-1 border-t border-line pt-4 text-sm">
        <Button variant="ghost" size="sm" onClick={flow.toggleRecovery}>
          {flow.useRecovery
            ? t("mfa.secondStep.useApp")
            : t("mfa.secondStep.useRecovery")}
        </Button>
        <Button variant="ghost" size="sm" onClick={onStartOver}>
          {t("mfa.secondStep.startOver")}
        </Button>
      </div>
    </form>
  );
}
