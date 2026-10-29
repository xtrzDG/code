/**
 * The workspace section (`../workspace.ts`) in Italian: a draft awaiting native
 * review, composed here so the section file stays small.
 */

import type { Translation } from "../../../translate";
import type { workspaceEn } from "../workspace";
import { adminIt } from "./admin.it";
import { adminActionsIt } from "./adminActions.it";
import { adminChurnIt } from "./adminChurn.it";
import { adminIncidentIt } from "./adminIncident.it";
import { adminMetricsIt } from "./adminMetrics.it";
import { adminReplyGuardIt } from "./adminReplyGuard.it";
import { adminReplySpeedIt } from "./adminReplySpeed.it";
import { adminSecurityIt } from "./adminSecurity.it";
import { adminSpendIt } from "./adminSpend.it";
import { adminStoryIt } from "./adminStory.it";
import { adminSystemIt } from "./adminSystem.it";
import { adminTeamIt } from "./adminTeam.it";
import { billingIt } from "./billing.it";
import { billingCardIt } from "./billingCard.it";
import { billingLifecycleIt } from "./billingLifecycle.it";
import { apiIntegrationsIt } from "./apiIntegrations.it";
import { calendarSyncIt } from "./calendarSync.it";
import { callSettingsIt } from "./callSettings.it";
import { channelPagesIt } from "./channelPages.it";
import { channelSetupIt } from "./channelSetup.it";
import { channelsIt } from "./channels.it";
import { workspaceCommonIt } from "./common.it";
import { customerMemoryIt } from "./customerMemory.it";
import { dataExportsIt } from "./dataExports.it";
import { dataTasksIt } from "./dataTasks.it";
import { providerCircuitsIt } from "./providerCircuits.it";
import { formFieldsIt } from "./formFields.it";
import { loginOptionsIt } from "./loginOptions.it";
import { metaConnectIt } from "./metaConnect.it";
import { notificationsIt } from "./notifications.it";
import { phoneNumbersIt } from "./phoneNumbers.it";
import { privacyNoticeIt } from "./privacyNotice.it";
import { privacyRetentionIt } from "./privacyRetention.it";
import { qualityIt } from "./quality.it";
import { quickRepliesIt } from "./quickReplies.it";
import { reviewSettingsIt } from "./reviewSettings.it";
import { settingsIt } from "./settings.it";
import { settingsRecordsIt } from "./settingsRecords.it";
import { shareIt } from "./share.it";
import { widgetSitesIt } from "./widgetSites.it";

export const workspaceIt: Translation<typeof workspaceEn> = {
  workspace: workspaceCommonIt,
  channels: channelsIt,
  channelPages: channelPagesIt,
  channelSetup: channelSetupIt,
  metaConnect: metaConnectIt,
  loginOptions: loginOptionsIt,
  billing: billingIt,
  billingLifecycle: billingLifecycleIt,
  billingCard: billingCardIt,
  settings: { ...settingsIt, ...settingsRecordsIt },
  notifications: notificationsIt,
  callSettings: callSettingsIt,
  phoneNumbers: phoneNumbersIt,
  reviewSettings: reviewSettingsIt,
  calendarSync: calendarSyncIt,
  apiIntegrations: apiIntegrationsIt,
  quickReplies: quickRepliesIt,
  admin: adminIt,
  adminSecurity: adminSecurityIt,
  adminActions: adminActionsIt,
  adminMetrics: adminMetricsIt,
  adminChurn: adminChurnIt,
  adminStory: adminStoryIt,
  adminReplySpeed: adminReplySpeedIt,
  adminReplyGuard: adminReplyGuardIt,
  adminSystem: adminSystemIt,
  adminTeam: adminTeamIt,
  adminIncident: adminIncidentIt,
  share: shareIt,
  privacyNotice: privacyNoticeIt,
  dataExports: dataExportsIt,
  quality: qualityIt,
  customerMemory: customerMemoryIt,
  privacyRetention: privacyRetentionIt,
  widgetSites: widgetSitesIt,
  adminSpend: adminSpendIt,
  dataTasks: dataTasksIt,
  providerCircuits: providerCircuitsIt,
  formFields: formFieldsIt,
};
