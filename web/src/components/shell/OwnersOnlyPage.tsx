"use client";

import { useBusiness } from "@/components/business/BusinessContext";
import { IconShield } from "@/components/icons";
import { ButtonLink, Card, UserSentence } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { businessPath } from "@/lib/navigation";

/**
 * Instead of a page a staff member's role does not open (an old link to
 * settings, say): what it is and the way back. The sections a role cannot
 * open are not in its navigation at all.
 */
export function OwnersOnlyPage() {
  const { t } = useI18n();
  const { business } = useBusiness();
  return (
    <Card className="mx-auto mt-6 max-w-lg">
      <div className="flex flex-col items-center px-6 py-10 text-center">
        <div className="mb-4 flex size-12 items-center justify-center rounded-2xl border border-line bg-surface-muted text-ink-muted" aria-hidden>
          <IconShield className="size-6" />
        </div>
        <h1 className="text-lg font-semibold text-ink">{t("navigation.ownerOnlyTitle")}</h1>
        <p className="mt-2 max-w-md text-sm text-ink-muted">
          <UserSentence text={t("navigation.ownerOnlyDescription")} values={{ business: business.name }} />
        </p>
        <ButtonLink href={businessPath(business.id)} className="mt-6">
          {t("navigation.toOverview")}
        </ButtonLink>
      </div>
    </Card>
  );
}
