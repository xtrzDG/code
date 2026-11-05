"use client";

/**
 * The quick actions above the reply box, in reach of the thumb: Resolve
 * (while the conversation waits for a person), Call (when the customer's
 * number is known) and Book. Each is a large target; the row scrolls
 * sideways on the narrowest phones rather than wrapping.
 */

import { IconCalendar, IconCheck, IconPhone } from "@/components/icons";
import { buttonClasses, Button } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

const ACTION = "h-10 shrink-0 rounded-full px-4";

export function ComposerActions({
  canResolve,
  isResolving,
  phone,
  canBook,
  onResolve,
  onBook,
}: {
  canResolve: boolean;
  isResolving: boolean;
  phone: string | null;
  canBook: boolean;
  onResolve: () => void;
  onBook: () => void;
}) {
  const { t } = useI18n();
  if (!canResolve && !phone && !canBook) {
    return null;
  }
  return (
    <div role="group" aria-label={t("inboxCard.actions.label")} className="-mx-1 flex gap-2 overflow-x-auto px-1 pb-2 [scrollbar-width:none]">
      {canResolve ? (
        <Button
          className={ACTION}
          leadingIcon={<IconCheck className="size-4" aria-hidden />}
          onClick={onResolve}
          isLoading={isResolving}
          title={t("inboxCard.actions.resolveHint")}
        >
          {t("inboxCard.actions.resolve")}
        </Button>
      ) : null}
      {phone ? (
        <a
          href={`tel:${phone}`}
          aria-label={t("inboxCard.actions.callLabel", { phone })}
          className={cn(buttonClasses({ variant: "secondary", className: ACTION }))}
        >
          <IconPhone className="size-4" aria-hidden />
          <span>{t("inboxCard.actions.call")}</span>
        </a>
      ) : null}
      {canBook ? (
        <Button
          variant="secondary"
          className={ACTION}
          leadingIcon={<IconCalendar className="size-4" aria-hidden />}
          onClick={onBook}
        >
          {t("inboxCard.actions.book")}
        </Button>
      ) : null}
    </div>
  );
}
