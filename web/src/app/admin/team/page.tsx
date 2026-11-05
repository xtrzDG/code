import type { Metadata } from "next";

import { getI18n } from "@/i18n/server";

import { TeamScreen } from "../_components/team/TeamScreen";

export async function generateMetadata(): Promise<Metadata> {
  const { t } = await getI18n();
  return { title: t("adminTeam.title") };
}

/** The platform admin team and its roles (/v1/admin/team). */
export default function AdminTeamPage() {
  return <TeamScreen />;
}
