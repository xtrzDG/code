"use client";

import { useEffect } from "react";

import { IconAlert } from "@/components/icons";
import { Button, ButtonLink, EmptyState } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { HOME_PATH } from "@/lib/navigation";

/** Unexpected errors of a page (Server Component data loads included). */
export default function ErrorPage({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  const { t } = useI18n();

  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <main className="mx-auto flex min-h-[60dvh] max-w-lg items-center px-4">
      <EmptyState
        className="w-full rounded-2xl border border-line bg-surface"
        icon={<IconAlert className="size-6" />}
        title={t("errors.title")}
        description={[t("errors.description"), error.digest ? t("common.requestId", { id: error.digest }) : null]
          .filter(Boolean)
          .join(" ")}
        action={
          <div className="flex flex-wrap justify-center gap-3">
            <Button onClick={reset}>{t("common.retry")}</Button>
            <ButtonLink href={HOME_PATH} variant="secondary">
              {t("errors.backHome")}
            </ButtonLink>
          </div>
        }
      />
    </main>
  );
}
