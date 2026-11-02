"use client";

import { useState } from "react";

import { Badge, Button, Card, ErrorState, SkeletonText } from "@/components/ui";
import { useToast } from "@/components/ui/Toast";
import { useI18n } from "@/i18n/client";
import { formatNumber } from "@/lib/format";

import {
  BRAKE_TONES,
  brakeState,
  type PlatformBrakes,
} from "../../_lib/platformBrakes";
import { usePlatformBrakes } from "../../_lib/usePlatformBrakes";
import { ActionDialog } from "../client/actions/ActionDialog";
import { useSystemFormat } from "./useSystemFormat";

/**
 * The platform's brakes: whether every assistant answers, is paused by a
 * SUPER admin (who, when, why) or is stopped by the daily budget, today's
 * share of the budget, and, for SUPER admins, "Pause every assistant" or
 * "Resume" with the reason the audit log keeps.
 */
export function PlatformBrakesCard({ canPause }: { canPause: boolean }) {
  const { t } = useI18n();
  const toast = useToast();
  const { brakes, setPaused, isChanging, changeError } = usePlatformBrakes();
  const [isAsking, setAsking] = useState(false);
  const title = t("platformBrakes.brakes.title");
  const data = brakes.data;

  if (brakes.error?.status === 403) {
    return null;
  }

  const confirm = async (reason: string) => {
    if (!data) return;
    if (await setPaused(!data.is_paused, reason)) {
      setAsking(false);
      toast.success(
        t(
          data.is_paused
            ? "platformBrakes.brakes.resumed"
            : "platformBrakes.brakes.paused",
        ),
      );
    }
  };

  return (
    <Card
      aria-label={title}
      title={title}
      description={t("platformBrakes.brakes.description")}
      actions={
        data && canPause ? (
          <Button
            variant={data.is_paused ? "primary" : "danger"}
            onClick={() => setAsking(true)}
          >
            {t(
              data.is_paused
                ? "platformBrakes.brakes.resume"
                : "platformBrakes.brakes.pause",
            )}
          </Button>
        ) : undefined
      }
    >
      {brakes.error && !data ? (
        <ErrorState error={brakes.error} onRetry={brakes.reload} />
      ) : !data ? (
        <SkeletonText lines={2} />
      ) : (
        <BrakesState brakes={data} />
      )}
      {data ? (
        <ActionDialog
          key={String(isAsking)}
          open={isAsking}
          title={t(
            data.is_paused
              ? "platformBrakes.brakes.resumeTitle"
              : "platformBrakes.brakes.pauseTitle",
          )}
          description={t(
            data.is_paused
              ? "platformBrakes.brakes.resumeDescription"
              : "platformBrakes.brakes.pauseDescription",
          )}
          confirmLabel={t(
            data.is_paused
              ? "platformBrakes.brakes.resume"
              : "platformBrakes.brakes.pause",
          )}
          tone={data.is_paused ? "primary" : "danger"}
          isPending={isChanging}
          error={changeError}
          onClose={() => setAsking(false)}
          onConfirm={confirm}
        />
      ) : null}
    </Card>
  );
}

function BrakesState({ brakes }: { brakes: PlatformBrakes }) {
  const { t, locale } = useI18n();
  const format = useSystemFormat();
  const state = brakeState(brakes);
  const percent = brakes.budget_used_percent ?? null;
  return (
    <div className="space-y-3">
      <p className="flex flex-wrap items-center gap-2">
        <Badge tone={BRAKE_TONES[state]}>
          {t(`platformBrakes.brakes.states.${state}`)}
        </Badge>
        {brakes.is_paused && brakes.changed_at ? (
          <span className="text-sm text-ink-muted">
            {t("platformBrakes.brakes.pausedSince", {
              time: format.when(brakes.changed_at),
            })}
          </span>
        ) : null}
      </p>
      {brakes.is_paused && brakes.reason ? (
        <p className="text-sm">
          <span className="text-ink-muted">
            {t("platformBrakes.brakes.reason")}{" "}
          </span>
          {brakes.reason}
        </p>
      ) : null}
      <p className="text-sm text-ink-muted">
        {percent === null
          ? t("platformBrakes.brakes.noBudget")
          : t("platformBrakes.brakes.budget", {
              percent: formatNumber(percent, locale),
              stop: formatNumber(brakes.stop_percent, locale),
            })}
      </p>
    </div>
  );
}
