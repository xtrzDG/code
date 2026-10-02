"use client";

import { Button } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

import type { GeneralSettings } from "../../_lib/useGeneralSettings";

/** Discard and save; it sticks to the bottom of the screen while there are unsaved changes. */
export function GeneralSaveBar({ settings }: { settings: GeneralSettings }) {
  const { t } = useI18n();
  const { isDirty, isSaving, discard } = settings;
  return (
    <div
      className={cn(
        "flex flex-col-reverse gap-3 sm:flex-row sm:items-center sm:justify-end",
        isDirty &&
          "sticky bottom-0 z-10 -mx-4 border-t border-line bg-canvas/95 px-4 py-3 backdrop-blur sm:mx-0 sm:rounded-xl sm:border sm:px-4",
      )}
    >
      {isDirty ? <p className="text-sm text-ink-muted sm:mr-auto">{t("settings.general.unsaved")}</p> : null}
      <Button variant="secondary" disabled={!isDirty || isSaving} onClick={discard}>
        {t("settings.general.discard")}
      </Button>
      <Button type="submit" isLoading={isSaving} loadingText={t("common.saving")} disabled={!isDirty}>
        {t("settings.general.save")}
      </Button>
    </div>
  );
}
