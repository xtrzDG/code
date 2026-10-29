"use client";

import { useState } from "react";

import type { SecondStepRequired } from "@/api/auth";
import { AuthenticatorSetup } from "@/components/security/AuthenticatorSetup";
import { OneTimeCodeField } from "@/components/security/OneTimeCodeField";
import { RecoveryCodesPanel } from "@/components/security/RecoveryCodesPanel";
import { Button, Field, Input } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { RECOVERY_CODE_EXAMPLE } from "@/lib/security/secondFactor";

import { usePasskeyStep } from "../_lib/usePasskeyStep";
import { useSecondStep } from "../_lib/useSecondStep";
import {
  PasskeyEnrollmentChoice,
  PasskeySignInPanel,
  StepHeading as Heading,
} from "./PasskeyStepPanels";

/**
 * Step three for people with a second factor (and every platform admin):
 * a passkey first when they have one, else the authenticator code or a
 * recovery code; an admin without a second factor adds a passkey (or
 * sets up the app) here and saves the recovery codes.
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
  const passkey = usePasskeyStep(step, flow.accept);
  const [useCode, setUseCode] = useState(false);
  const [useApp, setUseApp] = useState(false);

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

  if (flow.requiresEnrollment && passkey.canEnroll && !useApp && !flow.enrollment) {
    return (
      <PasskeyEnrollmentChoice
        isWorking={passkey.isWorking}
        isStartingApp={flow.isStartingSetup}
        problem={passkey.problem ?? flow.problem}
        onAddPasskey={passkey.enroll}
        onUseApp={() => {
          setUseApp(true);
          void flow.startSetup();
        }}
        onStartOver={onStartOver}
      />
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

  if (passkey.canSignIn && !useCode) {
    return (
      <PasskeySignInPanel
        isWorking={passkey.isWorking}
        problem={passkey.problem}
        onUsePasskey={passkey.signIn}
        onUseCode={passkey.hasCodes ? () => setUseCode(true) : null}
        onStartOver={onStartOver}
      />
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
              autoFocus
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
          autoFocus
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
        {passkey.canSignIn ? (
          <Button variant="ghost" size="sm" onClick={() => setUseCode(false)}>
            {t("passkeys.signIn.usePasskey")}
          </Button>
        ) : null}
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
