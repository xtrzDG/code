import { pageMetadata } from "@/components/business/pageMetadata";

import { TeamTab } from "../_components/TeamTab";
import { TwoFactorRequirementCard } from "../_components/team/TwoFactorRequirementCard";

export const generateMetadata = pageMetadata("settings/team");

/**
 * Settings → Team: owners and staff, invitations and roles; below, whether
 * the team must sign in with an authenticator app.
 */
export default function SettingsTeamPage() {
  return (
    <div className="space-y-6">
      <TeamTab />
      <TwoFactorRequirementCard />
    </div>
  );
}
