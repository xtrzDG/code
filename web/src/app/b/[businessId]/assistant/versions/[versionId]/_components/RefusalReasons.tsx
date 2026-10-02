"use client";

import type { ApiError } from "@/api/errors";
import { IconXCircle } from "@/components/content/icons";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import { isTestingRefusal, type GoLiveCheckCode, type Refusal, type RefusalCode } from "@/lib/assistant/goLive";

import { ActionButton, FixLink, GapList, useFixLinks } from "./goLiveFixes";

const REFUSAL_TEXTS: Record<RefusalCode, MessageKey> = {
  subscription_or_trial: "assistant.refusal.subscription_or_trial",
  dpa: "assistant.refusal.dpa",
  profile_gaps: "assistant.refusal.profile_gaps",
  staff_contact: "assistant.refusal.staff_contact",
  autotests: "assistant.refusal.autotests",
  voice_configuration: "assistant.refusal.voice_configuration",
  version_already_live: "assistant.refusal.version_already_live",
  version_archived: "assistant.refusal.version_archived",
  version_not_archived: "assistant.refusal.version_not_archived",
  force_publish_admin_only: "assistant.refusal.force_publish_admin_only",
};

/** Why publishing (or rolling back) was refused, from the API's reason codes, with links to fix each. */
export function RefusalReasons({
  reasons,
  error,
  onRunAutotests,
}: {
  reasons: readonly Refusal[];
  /** The refused request: its message is shown when the API named no reason. */
  error: ApiError | null;
  onRunAutotests?: () => void;
}) {
  const { t } = useI18n();
  const fixLinks = useFixLinks();

  if (reasons.length === 0) {
    return <p className="text-sm text-ink-muted">{error?.detail ?? t("errors.codes.conflict")}</p>;
  }

  return (
    <ul className="space-y-3">
      {reasons.map((reason, index) => {
        const text =
          reason.code === null
            ? reason.message
            : isTestingRefusal(reason)
              ? t("assistant.refusal.testing")
              : t(REFUSAL_TEXTS[reason.code]);
        const fix = reason.code !== null && reason.code in fixLinks ? fixLinks[reason.code as GoLiveCheckCode] : undefined;
        return (
          <li key={`${reason.code ?? "other"}-${index}`} className="flex items-start gap-3">
            <IconXCircle className="mt-0.5 size-5 shrink-0 text-danger" aria-hidden />
            <div className="min-w-0 flex-1 text-sm text-ink">
              <p>{text}</p>
              {reason.code === "profile_gaps" && reason.details.length > 0 ? (
                <div className="text-ink-muted">
                  <GapList kinds={reason.details} />
                </div>
              ) : null}
              {fix ? (
                <div className="mt-1">
                  <FixLink href={fix.href}>{t(fix.label)}</FixLink>
                </div>
              ) : null}
              {reason.code === "autotests" && !isTestingRefusal(reason) && onRunAutotests ? (
                <div className="mt-1">
                  <ActionButton onClick={onRunAutotests}>{t("assistant.autotests.run")}</ActionButton>
                </div>
              ) : null}
            </div>
          </li>
        );
      })}
    </ul>
  );
}
