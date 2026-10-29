/**
 * Texts of the cabinet sections: Channels, billing, settings (Calls, Quick replies, Reviews and Integrations among them), resources' calendars and the platform admin.
 *
 * Top-level keys are namespaces (one per section, e.g. `bookings`). They are
 * spread into en.ts and it.ts, so they must not clash
 * with the namespaces of the other dictionaries. The other languages are
 * type-checked against `en`.
 *
 * Each namespace (a large one in a few parts) lives in its own file per
 * language under `./workspace/`; this file composes them.
 */

import { adminEn } from "./workspace/admin.en";
import { adminIncidentEn } from "./workspace/adminIncident.en";
import { adminActionsEn } from "./workspace/adminActions.en";
import { adminStoryEn } from "./workspace/adminStory.en";
import { adminChurnEn } from "./workspace/adminChurn.en";
import { adminMetricsEn } from "./workspace/adminMetrics.en";
import { adminReplyGuardEn } from "./workspace/adminReplyGuard.en";
import { adminReplySpeedEn } from "./workspace/adminReplySpeed.en";
import { adminSecurityEn } from "./workspace/adminSecurity.en";
import { adminSpendEn } from "./workspace/adminSpend.en";
import { adminSystemEn } from "./workspace/adminSystem.en";
import { dataTasksEn } from "./workspace/dataTasks.en";
import { providerCircuitsEn } from "./workspace/providerCircuits.en";
import { adminTeamEn } from "./workspace/adminTeam.en";
import { billingEn } from "./workspace/billing.en";
import { billingCardEn } from "./workspace/billingCard.en";
import { billingLifecycleEn } from "./workspace/billingLifecycle.en";
import { apiIntegrationsEn } from "./workspace/apiIntegrations.en";
import { calendarSyncEn } from "./workspace/calendarSync.en";
import { callSettingsEn } from "./workspace/callSettings.en";
import { channelSetupEn } from "./workspace/channelSetup.en";
import { channelPagesEn } from "./workspace/channelPages.en";
import { channelsEn } from "./workspace/channels.en";
import { customerMemoryEn } from "./workspace/customerMemory.en";
import { dataExportsEn } from "./workspace/dataExports.en";
import { formFieldsEn } from "./workspace/formFields.en";
import { workspaceCommonEn } from "./workspace/common.en";
import { loginOptionsEn } from "./workspace/loginOptions.en";
import { metaConnectEn } from "./workspace/metaConnect.en";
import { notificationsEn } from "./workspace/notifications.en";
import { phoneNumbersEn } from "./workspace/phoneNumbers.en";
import { privacyNoticeEn } from "./workspace/privacyNotice.en";
import { privacyRetentionEn } from "./workspace/privacyRetention.en";
import { qualityEn } from "./workspace/quality.en";
import { quickRepliesEn } from "./workspace/quickReplies.en";
import { reviewSettingsEn } from "./workspace/reviewSettings.en";
import { settingsEn } from "./workspace/settings.en";
import { settingsRecordsEn } from "./workspace/settingsRecords.en";
import { shareEn } from "./workspace/share.en";
import { widgetSitesEn } from "./workspace/widgetSites.en";

export const workspaceEn = {
  workspace: workspaceCommonEn,
  channels: channelsEn,
  channelPages: channelPagesEn,
  channelSetup: channelSetupEn,
  metaConnect: metaConnectEn,
  loginOptions: loginOptionsEn,
  billing: billingEn,
  billingLifecycle: billingLifecycleEn,
  billingCard: billingCardEn,
  settings: { ...settingsEn, ...settingsRecordsEn },
  notifications: notificationsEn,
  callSettings: callSettingsEn,
  phoneNumbers: phoneNumbersEn,
  reviewSettings: reviewSettingsEn,
  calendarSync: calendarSyncEn,
  apiIntegrations: apiIntegrationsEn,
  quickReplies: quickRepliesEn,
  admin: adminEn,
  adminSecurity: adminSecurityEn,
  adminActions: adminActionsEn,
  adminMetrics: adminMetricsEn,
  adminChurn: adminChurnEn,
  adminStory: adminStoryEn,
  adminReplySpeed: adminReplySpeedEn,
  adminReplyGuard: adminReplyGuardEn,
  adminSystem: adminSystemEn,
  adminTeam: adminTeamEn,
  adminIncident: adminIncidentEn,
  share: shareEn,
  privacyNotice: privacyNoticeEn,
  dataExports: dataExportsEn,
  quality: qualityEn,
  customerMemory: customerMemoryEn,
  privacyRetention: privacyRetentionEn,
  widgetSites: widgetSitesEn,
  adminSpend: adminSpendEn,
  dataTasks: dataTasksEn,
  providerCircuits: providerCircuitsEn,
  formFields: formFieldsEn,
} as const;

export { workspaceIt } from "./workspace/section.it";
