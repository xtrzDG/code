import { pageMetadata } from "@/components/business/pageMetadata";

import { TeamTab } from "../_components/TeamTab";

export const generateMetadata = pageMetadata("settings/team");

/** Settings → Team: owners and staff, invitations and roles. */
export default function SettingsTeamPage() {
  return <TeamTab />;
}
