"use client";

/**
 * The passkey parts of the sign-in's second step: answering with a
 * passkey (shown first when the person has one), and a platform admin's
 * choice of a first second factor (a passkey first, the authenticator app
 * second).
 */

import { Button } from "@/components/ui";
import { useI18n } from "@/i18n/client";

export function StepHeading({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="space-y-1.5">
      <h1 className="text-xl font-display tracking-tight text-ink">{title}</h1>
      <p className="text-sm text-ink-muted">{description}</p>
    </div>
  );
}

export function PasskeySignInPanel({
  isWorking,
  problem,
  onUsePasskey,
  onUseCode,
  onStartOver,
}: {
  isWorking: boolean;
  problem: string | null;
  onUsePasskey: () => void;
  onUseCode: (() => void) | null;
  onStartOver: () => void;
}) {
  const { t } = useI18n();
  return (
    <div className="space-y-5">
      <StepHeading
        title={t("mfa.secondStep.title")}
        description={t("passkeys.signIn.description")}
      />
      <Button
        fullWidth
        size="lg"
        autoFocus
        isLoading={isWorking}
        loadingText={t("passkeys.signIn.waiting")}
        onClick={onUsePasskey}
      >
        {t("passkeys.signIn.use")}
      </Button>
      {problem ? (
        <p className="text-sm text-danger" role="alert">
          {problem}
        </p>
      ) : null}
      <div className="flex flex-col items-center gap-1 border-t border-line pt-4 text-sm">
        {onUseCode ? (
          <Button variant="ghost" size="sm" onClick={onUseCode}>
            {t("passkeys.signIn.useCode")}
          </Button>
        ) : null}
        <Button variant="ghost" size="sm" onClick={onStartOver}>
          {t("mfa.secondStep.startOver")}
        </Button>
      </div>
    </div>
  );
}

export function PasskeyEnrollmentChoice({
  isWorking,
  isStartingApp,
  problem,
  onAddPasskey,
  onUseApp,
  onStartOver,
}: {
  isWorking: boolean;
  isStartingApp: boolean;
  problem: string | null;
  onAddPasskey: () => void;
  onUseApp: () => void;
  onStartOver: () => void;
}) {
  const { t } = useI18n();
  return (
    <div className="space-y-5">
      <StepHeading
        title={t("mfa.enrollment.title")}
        description={t("passkeys.enrollment.description")}
      />
      <div className="space-y-2">
        <Button
          fullWidth
          size="lg"
          isLoading={isWorking}
          loadingText={t("passkeys.adding")}
          onClick={onAddPasskey}
        >
          {t("passkeys.enrollment.add")}
        </Button>
        <Button
          fullWidth
          variant="secondary"
          isLoading={isStartingApp}
          loadingText={t("mfa.enrollment.starting")}
          disabled={isWorking}
          onClick={onUseApp}
        >
          {t("passkeys.enrollment.useApp")}
        </Button>
      </div>
      {problem ? (
        <p className="text-sm text-danger" role="alert">
          {problem}
        </p>
      ) : null}
      <div className="border-t border-line pt-4 text-center">
        <Button variant="ghost" size="sm" onClick={onStartOver}>
          {t("mfa.secondStep.startOver")}
        </Button>
      </div>
    </div>
  );
}
