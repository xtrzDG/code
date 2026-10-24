"use client";

import { useState } from "react";

import { useBusinessFormat } from "@/components/business/BusinessContext";
import { IconLink, IconRefresh } from "@/components/icons";
import { CopyButton } from "@/components/workspace/CopyButton";
import { Alert, Button, ConfirmDialog, Input, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { ResourceCalendarView } from "@/lib/resourceCalendar";

import { CalendarSection } from "./CalendarParts";
import type { ResourceCalendarState } from "./useResourceCalendar";

type Asking = "regenerate" | "stop" | null;

/**
 * The resource's bookings shared back as an iCal address (for Airbnb,
 * Booking.com or any calendar). The address is shown once, right after it
 * is made (only its hash is kept); a new one replaces it, and sharing can
 * stop. Both ask first: calendars reading the old address lose it at once.
 */
export function IcalExportSection({ calendar, view }: { calendar: ResourceCalendarState; view: ResourceCalendarView }) {
  const { t } = useI18n();
  const toast = useToast();
  const format = useBusinessFormat();
  const [address, setAddress] = useState<string | null>(null);
  const [asking, setAsking] = useState<Asking>(null);
  const shared = view.ical_export;

  const create = async () => {
    const result = await calendar.createExport.run();
    if (result.ok) {
      calendar.view.setData(result.data.calendar);
      setAddress(result.data.url);
      setAsking(null);
      toast.success(t("calendarSync.export.created"));
    }
  };

  const stop = async () => {
    const result = await calendar.removeExport.run();
    if (result.ok) {
      setAddress(null);
      setAsking(null);
      toast.success(t("calendarSync.export.stopped"));
    }
  };

  return (
    <CalendarSection title={t("calendarSync.export.title")} description={t("calendarSync.export.description")}>
      {address ? (
        <Alert tone="info" title={t("calendarSync.export.shownOnce")}>
          <div className="mt-2 flex flex-col gap-2 sm:flex-row">
            <Input readOnly value={address} dir="ltr" aria-label={t("calendarSync.export.copy")} className="font-mono text-xs" onFocus={(event) => event.target.select()} />
            <CopyButton value={address} label={t("calendarSync.export.copy")} className="shrink-0" />
          </div>
        </Alert>
      ) : null}
      {shared.is_on ? (
        <div className="space-y-3">
          <div className="space-y-0.5 text-sm">
            {shared.created_at ? <p className="text-ink">{t("calendarSync.export.on", { time: format.dateTime(shared.created_at) })}</p> : null}
            <p className="text-ink-subtle">
              {shared.last_read_at
                ? t("calendarSync.export.lastRead", { time: format.dateTime(shared.last_read_at) })
                : t("calendarSync.export.neverRead")}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button variant="secondary" size="sm" leadingIcon={<IconRefresh className="size-4" aria-hidden />} onClick={() => setAsking("regenerate")}>
              {t("calendarSync.export.regenerate")}
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setAsking("stop")}>
              {t("calendarSync.export.stop")}
            </Button>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          <p className="text-sm text-ink-subtle">{t("calendarSync.export.off")}</p>
          <Button
            variant="secondary"
            size="sm"
            leadingIcon={<IconLink className="size-4" aria-hidden />}
            isLoading={calendar.createExport.isPending}
            onClick={() => void create()}
          >
            {t("calendarSync.export.create")}
          </Button>
        </div>
      )}
      <ConfirmDialog
        open={asking === "regenerate"}
        tone="primary"
        title={t("calendarSync.export.regenerateTitle")}
        description={t("calendarSync.export.regenerateDescription")}
        confirmLabel={t("calendarSync.export.regenerate")}
        isPending={calendar.createExport.isPending}
        onConfirm={() => void create()}
        onClose={() => setAsking(null)}
      />
      <ConfirmDialog
        open={asking === "stop"}
        title={t("calendarSync.export.stopTitle")}
        description={t("calendarSync.export.stopDescription")}
        confirmLabel={t("calendarSync.export.stop")}
        isPending={calendar.removeExport.isPending}
        onConfirm={() => void stop()}
        onClose={() => setAsking(null)}
      />
    </CalendarSection>
  );
}
