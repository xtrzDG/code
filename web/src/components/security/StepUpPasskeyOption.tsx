"use client";

/**
 * The passkey way to "confirm it is you". Alone (`isOnly`: the person has
 * passkeys and no authenticator app, so nothing was sent) it is the whole
 * form, with a recovery code on request (never a login code: it must not
 * stand in for the second factor); beside a code form it is one button
 * above it.
 */

import { Button } from "@/components/ui";
import { useI18n } from "@/i18n/client";

export function StepUpPasskeyOption({
  isOnly,
  isWorking,
  problem,
  onConfirm,
  onUseRecoveryCode,
}: {
  isOnly: boolean;
  isWorking: boolean;
  problem: string | null;
  onConfirm: () => void;
  onUseRecoveryCode: () => void;
}) {
  const { t } = useI18n();
  const problemLine = problem ? (
    <p className="text-sm text-danger" role="alert">
      {problem}
    </p>
  ) : null;

  if (isOnly) {
    return (
      <div className="space-y-4">
        <p className="text-sm text-ink-muted">{t("passkeys.stepUp.description")}</p>
        {problemLine}
        <Button variant="ghost" size="sm" disabled={isWorking} onClick={onUseRecoveryCode}>
          {t("mfa.secondStep.useRecovery")}
        </Button>
      </div>
    );
  }
  return (
    <div className="space-y-3">
      <Button
        fullWidth
        variant="secondary"
        isLoading={isWorking}
        loadingText={t("passkeys.signIn.waiting")}
        onClick={onConfirm}
      >
        {t("passkeys.stepUp.use")}
      </Button>
      {problemLine}
      <p className="flex items-center gap-3 text-xs text-ink-subtle" aria-hidden>
        <span className="h-px flex-1 bg-line" />
        {t("passkeys.stepUp.orCode")}
        <span className="h-px flex-1 bg-line" />
      </p>
    </div>
  );
}
