import { ButtonLink, EmptyState } from "@/components/ui";
import { IconAlert } from "@/components/icons";
import { getI18n } from "@/i18n/server";
import { HOME_PATH } from "@/lib/navigation";

export default async function NotFound() {
  const { t } = await getI18n();
  return (
    <main className="mx-auto flex min-h-dvh max-w-lg items-center px-4">
      <EmptyState
        className="w-full rounded-2xl border border-line bg-surface"
        icon={<IconAlert className="size-6" />}
        title={t("errors.notFoundTitle")}
        description={t("errors.notFoundDescription")}
        action={<ButtonLink href={HOME_PATH}>{t("errors.backHome")}</ButtonLink>}
      />
    </main>
  );
}
