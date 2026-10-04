"use client";

/**
 * The owner's side of the support banner: who from platform support looks
 * in, why and until when; "End access"; and "Let support make changes"
 * for a chosen time (a fresh confirmation may be asked first). Staff see
 * the same without the controls.
 */

import { useId, useState } from "react";

import type { SupportAccessView } from "@/api/types";
import { Switch } from "@/components/content/Switch";
import { Button, ConfirmDialog, Select, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { formatTime } from "@/lib/format";
import { DEFAULT_WRITE_ACCESS_HOURS, WRITE_ACCESS_HOURS } from "@/lib/supportAccess";

import type { useSupportAccess } from "./useSupportAccess";

type SupportActions = ReturnType<typeof useSupportAccess>;

export function OwnerSupportPanel({
  view,
  isOwner,
  actions,
  timeZone,
}: {
  view: SupportAccessView;
  isOwner: boolean;
  actions: SupportActions;
  timeZone: string;
}) {
  const { t, tp, locale } = useI18n();
  const toast = useToast();
  const hintId = useId();
  const [hours, setHours] = useState<number>(DEFAULT_WRITE_ACCESS_HOURS);
  const [isEnding, setEnding] = useState(false);
  const time = (value: number) => formatTime(value, { locale, timeZone });
  const isAllowed = view.write_access?.is_allowed ?? false;
  const hoursLabel = (count: number) =>
    count === 24 ? t("supportAccess.owner.dayOption") : count === 168 ? t("supportAccess.owner.weekOption") : tp("supportAccess.owner.hourOptions", count);

  const toggle = async (next: boolean) => {
    if (await actions.setWriteAccess(next, next ? hours : null)) {
      toast.success(next ? t("supportAccess.owner.allowed") : t("supportAccess.owner.stopped"));
    }
  };
  const end = async () => {
    if (await actions.end()) {
      setEnding(false);
      toast.success(t("supportAccess.owner.ended"));
    }
  };

  return (
    <div className="space-y-3">
      {(view.sessions ?? []).length > 0 ? (
        <>
          <p className="font-medium text-ink">{t("supportAccess.owner.title")}</p>
          <ul className="space-y-1">
            {(view.sessions ?? []).map((session) => (
              <li key={session.grant_id} className="text-ink">
                <span dir="auto">
                  {t("supportAccess.owner.who", { name: session.admin_name ?? t("supportAccess.owner.someone"), reason: session.reason })}
                </span>{" "}
                <span className="text-ink-muted">{t("supportAccess.owner.until", { time: time(session.expires_at) })}</span>
              </li>
            ))}
          </ul>
        </>
      ) : null}
      <p className="text-ink-muted">
        {isAllowed && view.write_access?.expires_at
          ? t("supportAccess.owner.allowedUntil", { time: time(view.write_access.expires_at) })
          : t("supportAccess.owner.readOnly")}
      </p>
      {isOwner ? (
        <div className="flex flex-wrap items-center gap-x-4 gap-y-3">
          <div className="flex items-center gap-3">
            <Switch
              checked={isAllowed}
              onChange={(next) => void toggle(next)}
              label={t("supportAccess.owner.allow")}
              describedBy={hintId}
              disabled={actions.writeAccess.isPending}
            />
            <span className="text-ink">{t("supportAccess.owner.allow")}</span>
          </div>
          {isAllowed ? null : (
            <Select
              aria-label={t("supportAccess.owner.hours")}
              value={String(hours)}
              onChange={(event) => setHours(Number(event.target.value))}
              className="w-auto"
            >
              {WRITE_ACCESS_HOURS.map((option) => (
                <option key={option} value={option}>
                  {hoursLabel(option)}
                </option>
              ))}
            </Select>
          )}
          <Button variant="secondary" size="sm" className="ms-auto" onClick={() => setEnding(true)}>
            {t("supportAccess.owner.end")}
          </Button>
          <p id={hintId} className="w-full text-xs text-ink-subtle">
            {t("supportAccess.owner.allowHint")}
          </p>
        </div>
      ) : (
        <p className="text-xs text-ink-subtle">{t("supportAccess.owner.staff")}</p>
      )}
      <ConfirmDialog
        open={isEnding}
        onClose={() => setEnding(false)}
        onConfirm={end}
        isPending={actions.ending.isPending}
        error={actions.ending.error}
        title={t("supportAccess.owner.endTitle")}
        description={t("supportAccess.owner.endDescription")}
        confirmLabel={t("supportAccess.owner.end")}
      />
    </div>
  );
}
