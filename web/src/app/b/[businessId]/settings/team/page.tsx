import { pageMetadata } from "@/components/business/pageMetadata";

import { TeamTab } from "../_components/TeamTab";
import { RecordingPermissionCard } from "../_components/team/RecordingPermissionCard";
import { TwoFactorRequirementCard } from "../_components/team/TwoFactorRequirementCard";

export const generateMetadata = pageMetadata("settings/team");

/**
 * Settings → Team: owners and staff, invitations and roles; below, whether
 * the team must sign in with an authenticator app and whether staff may
 * play the call recordings.
 */
export default function SettingsTeamPage() {
  return (
    <div className="space-y-6">
      <TeamTab />
      <TwoFactorRequirementCard />
      <RecordingPermissionCard />
    </div>
  );
}
