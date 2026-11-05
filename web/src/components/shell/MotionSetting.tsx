"use client";

import { useMotionPreference } from "@/components/motion/MotionPreference";
import { Checkbox } from "@/components/ui";
import { useI18n } from "@/i18n/client";

/**
 * "Reduce motion": a choice of this browser, in the account menu, kept in
 * the `aw_motion` cookie (lib/motionPreference.ts). On, the cabinet keeps
 * still whatever the device says; off, it follows the device's own
 * setting (which always wins when it asks for less motion).
 */
export function MotionSetting() {
  const { t } = useI18n();
  const { preference, setPreference } = useMotionPreference();

  return (
    <Checkbox
      className="px-2.5 py-1"
      label={t("account.motion")}
      description={<span className="text-xs">{t("account.motionHint")}</span>}
      checked={preference === "reduce"}
      onChange={(event) => setPreference(event.target.checked ? "reduce" : "system")}
    />
  );
}
