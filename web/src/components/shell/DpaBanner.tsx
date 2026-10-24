"use client";

/**
 * Over an owner's cabinet when a new version of the data processing
 * agreement replaces the one the business accepted: which version, the day
 * it is due (30 days after its date) and a link to read and accept it in
 * Settings → Privacy. Hidden for staff, once accepted, and on that page.
 */

import Link from "next/link";
import { usePathname } from "next/navigation";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useQuery } from "@/api/useQuery";
import { IconFile } from "@/components/icons";
import { buttonClasses } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { calendarDayMoment, dpaReacceptance } from "@/lib/dpaNotice";
import { formatDate } from "@/lib/format";
import { businessPath } from "@/lib/navigation";
import { todayInTimeZone } from "@/lib/specialDays";

import { useBusiness } from "../business/BusinessContext";

const PRIVACY_PAGE = "settings/privacy";

export function DpaBanner() {
  const { t, locale } = useI18n();
  const { business, isOwner } = useBusiness();
  const pathname = usePathname();
  const privacyPath = businessPath(business.id, PRIVACY_PAGE);
  const dpa = useQuery(
    queryKeys.settings.dpa(business.id),
    () => api.GET("/v1/businesses/{business_id}/dpa", { params: { path: { business_id: business.id } } }),
    { enabled: isOwner },
  );
  const notice = isOwner ? dpaReacceptance(dpa.data, todayInTimeZone(new Date(), business.timezone)) : null;

  if (notice === null || pathname === privacyPath) {
    return null;
  }
  const date = formatDate(calendarDayMoment(notice.dueOn), { locale, timeZone: "UTC", dateStyle: "long" });
  return (
    <section
      aria-label={t("dpaNotice.label")}
      data-testid="dpa-banner"
      className={cn(
        "mb-5 flex flex-wrap items-start gap-3 rounded-2xl border px-4 py-3 text-sm",
        notice.isOverdue ? "border-danger/40 bg-danger-soft/60" : "border-warning/40 bg-warning-soft/60",
      )}
    >
      <IconFile
        className={cn("mt-0.5 size-5 shrink-0", notice.isOverdue ? "text-danger" : "text-warning")}
        aria-hidden
      />
      <div className="min-w-0 flex-1 basis-60 space-y-1">
        <p className="font-medium text-ink">{t("dpaNotice.title", { version: notice.version })}</p>
        <p className="text-ink-muted">{t(notice.isOverdue ? "dpaNotice.overdue" : "dpaNotice.due", { date })}</p>
      </div>
      <Link href={`${privacyPath}#dpa`} className={buttonClasses({ variant: "secondary", size: "sm" })}>
        {t("dpaNotice.action")}
      </Link>
    </section>
  );
}
