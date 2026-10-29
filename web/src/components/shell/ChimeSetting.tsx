"use client";

import { Checkbox } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { playChime, unlockChime, useChimePreference } from "./chime";

/**
 * "Chime when someone needs a person": a choice of this device, in the
 * account menu. Turning it on plays the chime once, so the person knows
 * what to listen for (and the browser allows the page to make sound).
 */
export function ChimeSetting() {
  const { t } = useI18n();
  const [isOn, setIsOn] = useChimePreference();

  return (
    <Checkbox
      className="px-2.5 py-1"
      label={t("live.sound")}
      description={<span className="text-xs">{t("live.soundHint")}</span>}
      checked={isOn}
      onChange={(event) => {
        const next = event.target.checked;
        setIsOn(next);
        if (next) {
          unlockChime();
          window.setTimeout(playChime, 60);
        }
      }}
    />
  );
}
