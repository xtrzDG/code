"use client";

/**
 * A one-time tip over the Inbox, the Assistant's test page and Channels
 * (lib/help/helpTopics COACH_MARKS): what the page is for, "Got it" and
 * "Read the guide". Once either is pressed the API remembers it for the
 * person (PUT /v1/me/help/coach-marks/{key}), so it never shows again, on
 * any device, until they ask for the tips again in the help center.
 *
 * On a phone the tip is one line above the tab bar (its title, "Read the
 * guide" and a close button) instead of a card over half the first
 * screen, and it shows once: it is remembered as seen as soon as it has
 * been on screen, and stays for that visit.
 */

import { useEffect, useId, useState } from "react";

import { FadeIn } from "@/components/motion";
import { IconSparkles, IconX } from "@/components/icons";
import { Button, usePhoneChromeSnapshot } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { coachMarkFor, type CoachMark } from "@/lib/help/helpTopics";
import type { BusinessPage } from "@/lib/navigation";
import { COMPACT_SCREEN_QUERY, useMediaQuery } from "@/lib/useMediaQuery";

import { useHelpDrawer } from "./HelpProvider";
import { useHelpProgress } from "./useHelp";

/** How long the phone line is on screen before it counts as shown. */
const PHONE_SHOWN_AFTER_MS = 1_500;

export function CoachMarkSlot({ page }: { page: BusinessPage | null }) {
  const drawer = useHelpDrawer();
  const { progress, markSeen } = useHelpProgress();
  const isPhone = useMediaQuery(COMPACT_SCREEN_QUERY);
  const mark = coachMarkFor(page);
  // The phone line stays for the visit once it counted as shown (or until closed).
  const [shownOnPhone, setShownOnPhone] = useState<string | null>(null);
  const [closed, setClosed] = useState<string | null>(null);
  const markKey = mark?.key ?? null;
  const isUnseen = Boolean(markKey && progress.data && !progress.data.seen_coach_marks.includes(markKey));

  useEffect(() => {
    if (!isPhone || !isUnseen || !markKey) {
      return;
    }
    const timer = window.setTimeout(() => {
      setShownOnPhone(markKey);
      void markSeen(markKey);
    }, PHONE_SHOWN_AFTER_MS);
    return () => window.clearTimeout(timer);
  }, [isPhone, isUnseen, markKey, markSeen]);

  if (!mark || closed === mark.key || !(isUnseen || (isPhone && shownOnPhone === mark.key))) {
    return null;
  }
  const dismiss = () => {
    setClosed(mark.key);
    void markSeen(mark.key);
  };
  const readGuide = () => {
    drawer?.open(mark.article);
    dismiss();
  };
  return isPhone ? (
    <PhoneCoachLine mark={mark} onRead={readGuide} onClose={dismiss} />
  ) : (
    <CoachCard mark={mark} onRead={readGuide} onClose={dismiss} />
  );
}

interface CoachProps {
  mark: CoachMark;
  onRead: () => void;
  onClose: () => void;
}

function CoachCard({ mark, onRead, onClose }: CoachProps) {
  const { t } = useI18n();
  const titleId = useId();
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
          <Button size="sm" onClick={onClose}>
            {t("coachMarks.gotIt")}
          </Button>
          <Button size="sm" variant="ghost" aria-haspopup="dialog" onClick={onRead}>
            {t("coachMarks.readGuide")}
          </Button>
        </div>
      </div>
    </FadeIn>
  );
}

/** One line above the tab bar (and above the page's floating action button, when there is one). */
function PhoneCoachLine({ mark, onRead, onClose }: CoachProps) {
  const { t } = useI18n();
  const titleId = useId();
  const { fab } = usePhoneChromeSnapshot();
  return (
    <FadeIn
      as="section"
      aria-labelledby={titleId}
      data-coach-mark={mark.key}
      data-coach-line=""
      className={cn(
        "fixed inset-x-3 z-30 flex min-h-11 items-center gap-2 rounded-xl border border-accent/30 bg-surface ps-3 shadow-lg lg:hidden",
        // Right above the tab bar, or above the page's floating action when it has one.
        fab ? "bottom-[calc(9rem+env(safe-area-inset-bottom))]" : "bottom-[calc(4.75rem+env(safe-area-inset-bottom))]",
      )}
    >
      <IconSparkles className="size-4 shrink-0 text-accent" aria-hidden />
      <button
        type="button"
        aria-haspopup="dialog"
        onClick={onRead}
        className="min-h-11 min-w-0 flex-1 cursor-pointer truncate py-2 text-start text-sm font-medium text-ink focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-focus"
      >
        <span id={titleId}>{t(`coachMarks.${mark.key}.title`)}</span>
        <span className="sr-only">. {t("coachMarks.readGuide")}</span>
      </button>
      <button
        type="button"
        onClick={onClose}
        aria-label={t("coachMarks.gotIt")}
        className="flex size-11 shrink-0 cursor-pointer items-center justify-center rounded-xl text-ink-muted hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-focus"
      >
        <IconX className="size-4" aria-hidden />
      </button>
    </FadeIn>
  );
}
