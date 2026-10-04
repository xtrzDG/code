"use client";

/**
 * A one-time tip over the Inbox, the Assistant's test page and Channels
 * (lib/help/helpTopics COACH_MARKS): what the page is for, "Got it" and
 * "Read the guide". Once either is pressed the API remembers it for the
 * person (PUT /v1/me/help/coach-marks/{key}), so it never shows again, on
 * any device, until they ask for the tips again in the help center.
 */

import { useId } from "react";

import { FadeIn } from "@/components/motion";
import { IconSparkles } from "@/components/icons";
import { Button } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { coachMarkFor } from "@/lib/help/helpTopics";
import type { BusinessPage } from "@/lib/navigation";

import { useHelpDrawer } from "./HelpProvider";
import { useHelpProgress } from "./useHelp";

export function CoachMarkSlot({ page }: { page: BusinessPage | null }) {
  const { t } = useI18n();
  const titleId = useId();
  const drawer = useHelpDrawer();
  const { progress, markSeen } = useHelpProgress();
  const mark = coachMarkFor(page);

  if (!mark || !progress.data || progress.data.seen_coach_marks.includes(mark.key)) {
    return null;
  }
  const readGuide = () => {
    drawer?.open(mark.article);
    void markSeen(mark.key);
  };
  return (
    <FadeIn
      as="section"
      aria-labelledby={titleId}
      data-coach-mark={mark.key}
      className="mb-5 flex gap-3 rounded-2xl border border-accent/30 bg-accent-soft px-4 py-3.5"
    >
      <IconSparkles className="mt-0.5 size-5 shrink-0 text-accent" aria-hidden />
      <div className="min-w-0 flex-1 space-y-1">
        <p className="text-xs font-semibold tracking-wide text-accent-ink uppercase">{t("coachMarks.label")}</p>
        <p id={titleId} className="text-sm font-semibold text-ink">
          {t(`coachMarks.${mark.key}.title`)}
        </p>
        <p className="text-sm text-ink-muted">{t(`coachMarks.${mark.key}.body`)}</p>
        <div className="flex flex-wrap gap-2 pt-2">
          <Button size="sm" onClick={() => void markSeen(mark.key)}>
            {t("coachMarks.gotIt")}
          </Button>
          <Button size="sm" variant="ghost" aria-haspopup="dialog" onClick={readGuide}>
            {t("coachMarks.readGuide")}
          </Button>
        </div>
      </div>
    </FadeIn>
  );
}
