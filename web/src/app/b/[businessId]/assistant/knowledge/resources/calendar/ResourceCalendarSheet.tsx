"use client";

import { useBusinessFormat } from "@/components/business/BusinessContext";
import { IconRefresh } from "@/components/icons";
import { Button, ErrorState, LoadingRegion, Sheet, SkeletonText, UserSentence, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { BookingSystemSection } from "./BookingSystemSection";
import { BusyTimesList } from "./BusyTimesList";
import { GoogleCalendarSection } from "./GoogleCalendarSection";
import { IcalExportSection } from "./IcalExportSection";
import { IcalImportSection } from "./IcalImportSection";
import { useResourceCalendar } from "./useResourceCalendar";

export interface CalendarResource {
  id: string;
  name: string;
}

function SheetBody({ resourceId }: { resourceId: string }) {
  const { t } = useI18n();
  const toast = useToast();
  const format = useBusinessFormat();
  const calendar = useResourceCalendar(resourceId);
  const view = calendar.view.data;

  if (!view) {
    return calendar.view.error ? (
      <ErrorState error={calendar.view.error} onRetry={calendar.view.reload} />
    ) : (
      <LoadingRegion label={t("common.loading")} className="space-y-6">
        <SkeletonText lines={3} />
        <SkeletonText lines={4} />
      </LoadingRegion>
    );
  }

  const syncNow = async () => {
    const result = await calendar.sync.run();
    if (result.ok) {
      calendar.view.setData(result.data);
      toast.success(t("calendarSync.sheet.synced"));
    }
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-surface-muted px-3 py-2.5">
        <p className="text-sm text-ink-muted">
          {view.next_sync_at ? t("calendarSync.sheet.nextSync", { time: format.time(view.next_sync_at) }) : t("calendarSync.sheet.noSources")}
        </p>
        <Button
          variant="secondary"
          size="sm"
          leadingIcon={<IconRefresh className="size-4" aria-hidden />}
          isLoading={calendar.sync.isPending}
          onClick={() => void syncNow()}
        >
          {t("calendarSync.sheet.syncNow")}
        </Button>
      </div>
      <GoogleCalendarSection calendar={calendar} view={view} />
      <IcalImportSection calendar={calendar} view={view} />
      <BookingSystemSection calendar={calendar} view={view} />
      <IcalExportSection calendar={calendar} view={view} />
      <BusyTimesList blocks={view.upcoming_busy_times} />
    </div>
  );
}

/**
 * A resource's calendars (Knowledge → Resources and hours → Calendars):
 * the calendars whose busy times block it, the address that shares its
 * bookings back, and the busy times ahead; "Sync now" reads them again.
 */
export function ResourceCalendarSheet({ resource, onClose }: { resource: CalendarResource | null; onClose: () => void }) {
  const { t } = useI18n();
  return (
    <Sheet
      open={resource !== null}
      onClose={onClose}
      className="lg:w-[34rem]"
      title={resource ? <UserSentence text={t("calendarSync.sheet.title")} values={{ name: resource.name }} /> : null}
      description={t("calendarSync.sheet.description")}
    >
      {resource ? <SheetBody key={resource.id} resourceId={resource.id} /> : null}
    </Sheet>
  );
}
