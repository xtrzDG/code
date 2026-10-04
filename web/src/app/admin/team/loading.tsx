import { PageHeader } from "@/components/ui";
import { getI18n } from "@/i18n/server";

import { TeamSkeleton } from "../_components/team/TeamScreen";

export default async function AdminTeamLoading() {
  const { t } = await getI18n();
  return (
    <>
      <PageHeader title={t("adminTeam.title")} description={t("adminTeam.description")} />
      <TeamSkeleton />
    </>
  );
}
