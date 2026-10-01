"use client";

/** Small pieces shared by the dashboard, conversations, bookings, leads and handoffs pages. */

import type { ReactNode } from "react";

import { describeError } from "@/api/errors";
import { Alert, Button, Checkbox, Spinner } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

/** A phone number in E.164 as a call link (kept left-to-right in any language). */
export function PhoneLink({ phone, className }: { phone: string; className?: string }) {
  const { t } = useI18n();
  return (
    <a
      href={`tel:${phone}`}
      dir="ltr"
      className={cn("whitespace-nowrap text-accent tabular-nums hover:underline", className)}
      aria-label={t("insights.callPhone", { phone })}
    >
      {phone}
    </a>
  );
}

/** The customer's name (any script, so `dir="auto"`), or a neutral placeholder. */
export function CustomerName({ name, className }: { name: string | null | undefined; className?: string }) {
  const { t } = useI18n();
  return name ? (
    <span dir="auto" className={cn("break-words", className)}>
      {name}
    </span>
  ) : (
    <span className={cn("text-ink-muted italic", className)}>{t("insights.unknownCustomer")}</span>
  );
}

/** Reload button for a list; spins while a reload is running over shown data. */
export function RefreshButton({ onClick, isRefreshing }: { onClick: () => void; isRefreshing: boolean }) {
  const { t } = useI18n();
  return (
    <Button variant="secondary" onClick={onClick} disabled={isRefreshing} aria-busy={isRefreshing || undefined}>
      {isRefreshing ? <Spinner size="sm" /> : null}
      {t("insights.refresh")}
    </Button>
  );
}

/**
 * The end of a server-paged list: "show more" while the API has another
 * page, a spinner while it loads, and a retry when it failed.
 */
export function LoadMore({
  hasMore,
  isLoading,
  error,
  onMore,
  shownText,
}: {
  hasMore: boolean;
  isLoading: boolean;
  error: unknown;
  onMore: () => void;
  /** "Showing 50 of 120" when the total is known. */
  shownText?: string;
}) {
  const { t } = useI18n();
  if (!hasMore && !shownText) {
    return null;
  }
  return (
    <div className="flex flex-col items-center gap-2 py-4">
      {shownText ? (
        <p className="text-xs text-ink-subtle" aria-live="polite">
          {shownText}
        </p>
      ) : null}
      {error ? (
        <p className="text-xs text-danger" role="alert">
          {describeError(error, t).title}
        </p>
      ) : null}
      {hasMore ? (
        <Button variant="secondary" size="sm" onClick={onMore} isLoading={isLoading} loadingText={t("insights.loadingMore")}>
          {error ? t("common.retry") : t("insights.showMore")}
        </Button>
      ) : null}
    </div>
  );
}

/** The "include test activity" switch of the lists (sandbox conversations). */
export function IncludeTestToggle({
  checked,
  onChange,
  compact = false,
}: {
  checked: boolean;
  onChange: (value: boolean) => void;
  /** Without the explanation line (narrow filter bars). */
  compact?: boolean;
}) {
  const { t } = useI18n();
  return (
    <Checkbox
      label={t("insights.includeTest")}
      description={compact ? undefined : t("insights.includeTestHint")}
      title={compact ? t("insights.includeTestHint") : undefined}
      checked={checked}
      onChange={(event) => onChange(event.target.checked)}
    />
  );
}

/** A label/value row of a details list. */
export function DetailRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="grid grid-cols-1 gap-0.5 py-2 sm:grid-cols-[10rem_1fr] sm:gap-4">
      <dt className="text-sm text-ink-muted">{label}</dt>
      <dd className="min-w-0 text-sm text-ink">{children}</dd>
    </div>
  );
}

/** A reload failed while older data is still shown: say so and offer to retry. */
export function RefreshFailed({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  const { t } = useI18n();
  return (
    <Alert tone="warning" title={describeError(error, t).title}>
      <button type="button" onClick={onRetry} className="font-medium text-accent hover:underline">
        {t("common.retry")}
      </button>
    </Alert>
  );
}
