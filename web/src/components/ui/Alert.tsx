import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

import { IconAlert, IconCheck, IconInfo } from "../icons";

export type AlertTone = "info" | "success" | "warning" | "danger";

const TONES: Record<AlertTone, { className: string; icon: typeof IconInfo }> = {
  info: { className: "border-info/25 bg-info-soft text-info", icon: IconInfo },
  success: { className: "border-success/25 bg-success-soft text-success", icon: IconCheck },
  warning: { className: "border-warning/30 bg-warning-soft text-warning", icon: IconAlert },
  danger: { className: "border-danger/25 bg-danger-soft text-danger", icon: IconAlert },
};

/**
 * An inline message inside a page or form (not a toast). The `action`
 * (a button or link) sits beside the text when the alert is wide enough and
 * under it in narrow places (phones, side panels, dialogs).
 */
export function Alert({
  tone = "info",
  title,
  action,
  className,
  children,
}: {
  tone?: AlertTone;
  title?: ReactNode;
  action?: ReactNode;
  className?: string;
  children?: ReactNode;
}) {
  const { className: toneClass, icon: Icon } = TONES[tone];
  return (
    <div
      role={tone === "danger" ? "alert" : undefined}
      className={cn("flex gap-3 rounded-xl border px-4 py-3 text-sm", toneClass, className)}
    >
      <Icon className="mt-0.5 size-5 shrink-0" aria-hidden />
      {/* The alert's own width decides the layout (a container query), not the screen's. */}
      <div className="@container min-w-0 flex-1">
        <div className="flex flex-col items-start gap-3 @md:flex-row @md:items-center">
          <div className="w-full min-w-0 flex-1 space-y-1">
            {title ? <p className="font-medium">{title}</p> : null}
            {children ? <div className="text-ink-muted">{children}</div> : null}
          </div>
          {action ? <div className="flex max-w-full shrink-0 flex-wrap gap-2">{action}</div> : null}
        </div>
      </div>
    </div>
  );
}
