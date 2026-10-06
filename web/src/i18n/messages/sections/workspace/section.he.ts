/**
 * The workspace section (`../workspace.ts`) in Hebrew: a draft awaiting native
 * review, composed here so the section file stays small.
 */

import type { Translation } from "../../../translate";
import type { workspaceEn } from "../workspace";
import { adminHe } from "./admin.he";
import { adminActionsHe } from "./adminActions.he";
import { adminChurnHe } from "./adminChurn.he";
import { adminIncidentHe } from "./adminIncident.he";
import { adminMetricsHe } from "./adminMetrics.he";
import { adminReplyGuardHe } from "./adminReplyGuard.he";
import { adminReplySpeedHe } from "./adminReplySpeed.he";
import { adminSecurityHe } from "./adminSecurity.he";
import { adminSpendHe } from "./adminSpend.he";
import { adminStoryHe } from "./adminStory.he";
import { adminSystemHe } from "./adminSystem.he";
import { adminTeamHe } from "./adminTeam.he";
import { billingHe } from "./billing.he";
import { billingLifecycleHe } from "./billingLifecycle.he";
import { calendarSyncHe } from "./calendarSync.he";
import { callSettingsHe } from "./callSettings.he";
import { channelPagesHe } from "./channelPages.he";
import { channelSetupHe } from "./channelSetup.he";
import { channelsHe } from "./channels.he";
import { workspaceCommonHe } from "./common.he";
import { customerMemoryHe } from "./customerMemory.he";
import { dataExportsHe } from "./dataExports.he";
import { dataTasksHe } from "./dataTasks.he";
import { formFieldsHe } from "./formFields.he";
import { loginOptionsHe } from "./loginOptions.he";
import { notificationsHe } from "./notifications.he";
import { privacyNoticeHe } from "./privacyNotice.he";
import { privacyRetentionHe } from "./privacyRetention.he";
import { qualityHe } from "./quality.he";
import { quickRepliesHe } from "./quickReplies.he";
import { reviewSettingsHe } from "./reviewSettings.he";
import { settingsHe } from "./settings.he";
import { settingsRecordsHe } from "./settingsRecords.he";
import { shareHe } from "./share.he";
import { widgetSitesHe } from "./widgetSites.he";

export const workspaceHe: Translation<typeof workspaceEn> = {
  workspace: workspaceCommonHe,
  channels: channelsHe,
  channelPages: channelPagesHe,
  channelSetup: channelSetupHe,
  loginOptions: loginOptionsHe,
  billing: billingHe,
  billingLifecycle: billingLifecycleHe,
  settings: { ...settingsHe, ...settingsRecordsHe },
  notifications: notificationsHe,
  callSettings: callSettingsHe,
  reviewSettings: reviewSettingsHe,
  calendarSync: calendarSyncHe,
  quickReplies: quickRepliesHe,
  admin: adminHe,
  adminSecurity: adminSecurityHe,
  adminActions: adminActionsHe,
  adminMetrics: adminMetricsHe,
  adminChurn: adminChurnHe,
  adminStory: adminStoryHe,
  adminReplySpeed: adminReplySpeedHe,
  adminReplyGuard: adminReplyGuardHe,
  adminSystem: adminSystemHe,
  adminTeam: adminTeamHe,
  adminIncident: adminIncidentHe,
  share: shareHe,
  privacyNotice: privacyNoticeHe,
  dataExports: dataExportsHe,
  quality: qualityHe,
  customerMemory: customerMemoryHe,
  privacyRetention: privacyRetentionHe,
  widgetSites: widgetSitesHe,
  adminSpend: adminSpendHe,
  dataTasks: dataTasksHe,
  formFields: formFieldsHe,
};
