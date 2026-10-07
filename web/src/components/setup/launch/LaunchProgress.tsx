"use client";

/**
 * The launch under way: a glowing bar that fills as the assistant is
 * built, tried on test conversations and switched on, and the three stages
 * with their state (the checks counted as they run). Reduced motion keeps
 * the same states without the glide (the fill's transition is CSS). The
 * cabinet's "Apply changes" shows the same stages in its own words.
 */

import type { Schema } from "@/api/types";
import { IconAlert, IconCheck } from "@/components/icons";
import { Spinner } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import {
  LAUNCH_STAGES,
  launchProgress,
  stageStates,
  type LaunchStage,
  type StageState,
} from "@/lib/tunnel/launch";

function StageMark({ state }: { state: StageState }) {
  if (state === "done") {
    return (
      <span className="flex size-8 items-center justify-center rounded-full bg-success text-white shadow-[0_0_0_4px_var(--success-soft)]">
        <IconCheck className="size-4" aria-hidden />
      </span>
    );
  }
  if (state === "active") {
    return (
      <span className="flex size-8 items-center justify-center rounded-full bg-accent-soft text-accent shadow-[0_0_0_4px_var(--accent-soft)]">
        <Spinner size="sm" />
      </span>
    );
  }
  if (state === "stopped") {
    return (
      <span className="flex size-8 items-center justify-center rounded-full bg-warning-soft text-warning">
        <IconAlert className="size-4" aria-hidden />
      </span>
    );
  }
  return (
    <span
      className="block size-8 rounded-full border-2 border-dashed border-line-strong"
      aria-hidden
    />
  );
}

export function LaunchProgress({
  view,
  label,
  stageLabel,
}: {
  view: Schema<"ApplyChangesView">;
  /** The progress bar's name (the tunnel's by default). */
  label?: string;
  /** The name of each stage (the tunnel's by default). */
  stageLabel?: (stage: LaunchStage) => string;
}) {
  const { t } = useI18n();
  const states = stageStates(view);
  const progress = launchProgress(view);
  const isChecking = view.stage === "checking" && (view.checks_total ?? 0) > 0;

  return (
    <div className="space-y-6">
      {view.stage === "needs_attention" ? null : (
        <div
          role="progressbar"
          aria-label={label ?? t("tunnelLaunch.launch.stagesLabel")}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={Math.round(progress * 100)}
          className="relative h-3 overflow-hidden rounded-full bg-surface-muted ring-1 ring-line"
        >
          <span
            className="tunnel-rail-fill absolute inset-y-0 start-0 w-full rounded-full bg-[linear-gradient(90deg,var(--accent-solid),var(--success))] shadow-[0_0_24px_var(--accent-solid)]"
            style={{ transform: `scaleX(${Math.max(progress, 0.02)})` }}
          />
        </div>
      )}
      <ol className="space-y-3">
        {LAUNCH_STAGES.map((stage) => {
          const state = states[stage];
          return (
            <li
              key={stage}
              aria-current={state === "active" ? "step" : undefined}
              className={cn(
                "flex items-center gap-4 rounded-2xl border bg-surface/85 px-4 py-3 backdrop-blur-sm transition-colors",
                state === "active"
                  ? "border-accent/60"
                  : state === "stopped"
                    ? "border-warning/50"
                    : "border-line",
              )}
            >
              <StageMark state={state} />
              <span
                className={cn(
                  "min-w-0 flex-1 text-base",
                  state === "todo" ? "text-ink-muted" : "font-medium text-ink",
                )}
              >
                {stageLabel ? stageLabel(stage) : t(`tunnelLaunch.launch.stages.${stage}`)}
              </span>
              {stage === "checking" && isChecking ? (
                <span className="text-sm text-ink-muted tabular-nums">
                  {t("tunnelLaunch.launch.checks", {
                    done: view.checks_done ?? 0,
                    total: view.checks_total ?? 0,
                  })}
                </span>
              ) : null}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
