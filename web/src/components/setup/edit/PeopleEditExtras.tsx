"use client";

/**
 * What "People" of Assistant → Business profile has besides who gets the
 * conversations: the phone a call goes to when a caller asks for a
 * person, saved as it is typed, and the way to the rules of when the
 * assistant calls a person.
 */

import Link from "next/link";
import { useState } from "react";

import { IconArrowRight } from "@/components/icons";
import { useI18n } from "@/i18n/client";
import { profileSectionPath } from "@/lib/profile/sections";

import type { StepContext } from "../flow/stepContext";
import { PhoneField } from "./PhoneField";
import { useProfileField } from "./useProfileField";

export function PeopleEditExtras({ ctx }: { ctx: StepContext }) {
  const { t } = useI18n();
  const [phone, setPhone] = useState(ctx.wizard.profile.contacts.handoff_phone_number ?? "");
  const saved = useProfileField(ctx.businessId, phone.trim(), (value) => ({ contacts: { handoff_phone_number: value || null } }));

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-line bg-surface/85 p-5 backdrop-blur-sm sm:p-6">
        <div className="sm:max-w-md">
          <PhoneField
            label={t("profileEdit.people.handoffPhone")}
            hint={t("profileEdit.people.handoffPhoneHint")}
            value={phone}
            onChange={setPhone}
            error={saved.error}
          />
        </div>
      </section>
      <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-ink-muted">
        {t("profileEdit.people.rulesLink")}
        <Link
          href={profileSectionPath(ctx.businessId, "rules")}
          className="inline-flex min-h-9 items-center gap-1 rounded-lg font-medium text-accent underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-focus"
        >
          {t("profileEdit.people.openRules")}
          <IconArrowRight className="size-4 rtl:-scale-x-100" aria-hidden />
        </Link>
      </p>
    </div>
  );
}
