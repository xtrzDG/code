"use client";

/**
 * The first real customer, the first booking and the first booking while
 * the business was closed: each gets a toast with a small burst, once,
 * on whichever device sees it first (POST …/celebrate tells the API). Old
 * news and the owner's own test from a phone are acknowledged quietly
 * (`pendingCelebrations`). One toast at a time; it leaves by itself.
 */

import { AnimatePresence } from "motion/react";
import * as m from "motion/react-m";
import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { invalidate } from "@/api/queryCache";
import type { Schema } from "@/api/types";
import { useBusiness } from "@/components/business/BusinessContext";
import { IconStar, IconX } from "@/components/icons";
import { Burst } from "@/components/motion";
import { ButtonLink } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { tweenTransition } from "@/lib/motion";
import { businessPath, inboxPath } from "@/lib/navigation";
import { pendingCelebrations } from "@/lib/setupGuide/guide";

import { useSetupProgress } from "./useSetupProgress";

type Milestone = Schema<"ActivationMilestoneView">;
type CelebratedKind = "first_conversation" | "first_booking" | "first_after_hours_booking";

/** How long a celebration stays (ms). */
const SHOWN_MS = 9_000;

export function MilestoneCelebrations() {
  const { t } = useI18n();
  const { business } = useBusiness();
  const setup = useSetupProgress(business.id);
  const [current, setCurrent] = useState<Milestone | null>(null);
  const handled = useRef(new Set<string>());

  const celebrate = useCallback(
    (kind: Milestone["kind"]) => {
      void api
        .POST("/v1/businesses/{business_id}/setup/milestones/{kind}/celebrate", {
          params: { path: { business_id: business.id, kind } },
        })
        .then(() => invalidate(queryKeys.setup.all(business.id), { refetchActive: false }))
        .catch(() => undefined);
    },
    [business.id],
  );

  useEffect(() => {
    const { show, quiet } = pendingCelebrations(setup.data, Date.now());
    for (const milestone of quiet) {
      if (!handled.current.has(milestone.kind)) {
        handled.current.add(milestone.kind);
        celebrate(milestone.kind);
      }
    }
    if (current !== null) {
      return;
    }
    const next = show.find((milestone) => !handled.current.has(milestone.kind));
    if (next) {
      handled.current.add(next.kind);
      setCurrent(next);
      celebrate(next.kind);
    }
  }, [celebrate, current, setup.data]);

  useEffect(() => {
    if (current === null) {
      return;
    }
    const timer = setTimeout(() => setCurrent(null), SHOWN_MS);
    return () => clearTimeout(timer);
  }, [current]);

  const kind = current?.kind as CelebratedKind | undefined;
  return (
    <div className="pointer-events-none fixed inset-x-4 bottom-[calc(5.5rem+env(safe-area-inset-bottom))] z-50 flex justify-center sm:inset-x-auto sm:end-6 lg:bottom-6">
      <AnimatePresence>
        {kind ? (
          <m.div
            key={kind}
            role="status"
            aria-live="polite"
            initial={{ opacity: 0, y: 16, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8 }}
            transition={tweenTransition("slow", "emphasized")}
            className="pointer-events-auto relative w-full max-w-sm overflow-hidden rounded-2xl border border-line bg-surface p-4 shadow-lg"
          >
            <div className="relative flex gap-3">
              <span className="relative flex size-10 shrink-0 items-center justify-center rounded-full bg-accent-soft text-accent">
                <Burst />
                <IconStar className="size-5" aria-hidden />
              </span>
              <div className="min-w-0 flex-1 space-y-1">
                <p className="text-sm font-semibold text-ink">{t(`setupGuide.celebrations.${kind}.title`)}</p>
                <p className="text-sm text-ink-muted">{t(`setupGuide.celebrations.${kind}.description`)}</p>
                <ButtonLink
                  size="sm"
                  variant="ghost"
                  className="-ms-2"
                  href={kind === "first_conversation" ? inboxPath(business.id, "all") : businessPath(business.id, "bookings")}
                  onClick={() => setCurrent(null)}
                >
                  {t(kind === "first_conversation" ? "setupGuide.celebrations.openInbox" : "setupGuide.celebrations.openBookings")}
                </ButtonLink>
              </div>
              <button
                type="button"
                onClick={() => setCurrent(null)}
                aria-label={t("setupGuide.celebrations.close")}
                className="flex size-8 shrink-0 cursor-pointer items-center justify-center rounded-full text-ink-muted hover:bg-surface-muted focus-visible:outline-2 focus-visible:outline-focus"
              >
                <IconX className="size-4" aria-hidden />
              </button>
            </div>
          </m.div>
        ) : null}
      </AnimatePresence>
    </div>
  );
}
