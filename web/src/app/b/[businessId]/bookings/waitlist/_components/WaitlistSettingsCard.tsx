"use client";

import { useState } from "react";

import { Switch } from "@/components/content/Switch";
import { Button, Card, Field, InlineError, Select, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { holdOptions, type WaitlistSettings } from "../_lib/waitlistModel";
import type { WaitlistState } from "../_lib/useWaitlist";

/**
 * The owner's choices: keep a waitlist (the assistant offers it when a day
 * is full) and how long a freed place is held for the customer's answer.
 * Staff see the choices without changing them.
 */
export function WaitlistSettingsCard({ stored, state, canEdit }: { stored: WaitlistSettings; state: WaitlistState; canEdit: boolean }) {
  const { t, tp } = useI18n();
  const toast = useToast();
  const [isEnabled, setIsEnabled] = useState(stored.is_enabled);
  const [holdMinutes, setHoldMinutes] = useState(stored.hold_minutes);
  const { save, settings } = state;
  const isSame = isEnabled === stored.is_enabled && holdMinutes === stored.hold_minutes;
  const isLocked = !canEdit || save.isPending;

  const submit = async () => {
    const result = await save.run({ is_enabled: isEnabled, hold_minutes: holdMinutes });
    if (result.ok) {
      settings.setData(result.data);
      toast.success(t("waitlist.settings.saved"));
    }
  };

  return (
    <Card title={t("waitlist.settings.title")} description={t("waitlist.settings.description")}>
      <form
        noValidate
        className="space-y-5"
        onSubmit={(event) => {
          event.preventDefault();
          void submit();
        }}
      >
        <div className="flex items-start justify-between gap-4">
          <p className="min-w-0 text-sm font-medium text-ink">{t("waitlist.settings.toggle")}</p>
          <Switch checked={isEnabled} onChange={setIsEnabled} label={t("waitlist.settings.toggle")} disabled={isLocked} />
        </div>
        {isEnabled ? null : <p className="text-sm text-ink-muted">{t("waitlist.settings.off")}</p>}
        <Field label={t("waitlist.settings.hold")} hint={t("waitlist.settings.holdHint")}>
          {(control) => (
            <Select
              {...control}
              value={String(holdMinutes)}
              disabled={isLocked}
              onChange={(event) => setHoldMinutes(Number(event.target.value))}
            >
              {holdOptions(holdMinutes).map((minutes) => (
                <option key={minutes} value={minutes}>
                  {tp("waitlist.settings.holdOption", minutes, { count: minutes })}
                </option>
              ))}
            </Select>
          )}
        </Field>
        {canEdit ? (
          <>
            <InlineError error={save.error} />
            <div className="flex justify-end">
              <Button type="submit" disabled={isSame} isLoading={save.isPending} loadingText={t("common.saving")}>
                {t("waitlist.settings.save")}
              </Button>
            </div>
          </>
        ) : (
          <p className="text-sm text-ink-muted">{t("waitlist.settings.ownersOnly")}</p>
        )}
      </form>
    </Card>
  );
}
