/**
 * The workspace section (`../workspace.ts`) in German: a draft awaiting native
 * review, composed here so the section file stays small.
 */

import type { Translation } from "../../../translate";
import type { workspaceEn } from "../workspace";
import { adminDe } from "./admin.de";
import { adminActionsDe } from "./adminActions.de";
import { adminChurnDe } from "./adminChurn.de";
import { adminIncidentDe } from "./adminIncident.de";
import { adminMetricsDe } from "./adminMetrics.de";
import { adminReplyGuardDe } from "./adminReplyGuard.de";
import { adminReplySpeedDe } from "./adminReplySpeed.de";
import { adminSecurityDe } from "./adminSecurity.de";
import { adminSpendDe } from "./adminSpend.de";
import { adminStoryDe } from "./adminStory.de";
import { adminSystemDe } from "./adminSystem.de";
import { adminTeamDe } from "./adminTeam.de";
import { billingDe } from "./billing.de";
import { billingLifecycleDe } from "./billingLifecycle.de";
import { calendarSyncDe } from "./calendarSync.de";
import { callSettingsDe } from "./callSettings.de";
import { channelPagesDe } from "./channelPages.de";
import { channelSetupDe } from "./channelSetup.de";
import { channelsDe } from "./channels.de";
import { workspaceCommonDe } from "./common.de";
import { customerMemoryDe } from "./customerMemory.de";
import { dataExportsDe } from "./dataExports.de";
import { dataTasksDe } from "./dataTasks.de";
import { formFieldsDe } from "./formFields.de";
import { loginOptionsDe } from "./loginOptions.de";
import { notificationsDe } from "./notifications.de";
import { privacyNoticeDe } from "./privacyNotice.de";
import { privacyRetentionDe } from "./privacyRetention.de";
import { qualityDe } from "./quality.de";
import { quickRepliesDe } from "./quickReplies.de";
import { reviewSettingsDe } from "./reviewSettings.de";
import { settingsDe } from "./settings.de";
import { settingsRecordsDe } from "./settingsRecords.de";
import { shareDe } from "./share.de";
import { widgetSitesDe } from "./widgetSites.de";

export const workspaceDe: Translation<typeof workspaceEn> = {
  workspace: workspaceCommonDe,
  channels: channelsDe,
  channelPages: channelPagesDe,
  channelSetup: channelSetupDe,
  loginOptions: loginOptionsDe,
  billing: billingDe,
  billingLifecycle: billingLifecycleDe,
  settings: { ...settingsDe, ...settingsRecordsDe },
  notifications: notificationsDe,
  callSettings: callSettingsDe,
  reviewSettings: reviewSettingsDe,
  calendarSync: calendarSyncDe,
  quickReplies: quickRepliesDe,
  admin: adminDe,
  adminSecurity: adminSecurityDe,
  adminActions: adminActionsDe,
  adminMetrics: adminMetricsDe,
  adminChurn: adminChurnDe,
  adminStory: adminStoryDe,
  adminReplySpeed: adminReplySpeedDe,
  adminReplyGuard: adminReplyGuardDe,
  adminSystem: adminSystemDe,
  adminTeam: adminTeamDe,
  adminIncident: adminIncidentDe,
  share: shareDe,
  privacyNotice: privacyNoticeDe,
  dataExports: dataExportsDe,
  quality: qualityDe,
  customerMemory: customerMemoryDe,
  privacyRetention: privacyRetentionDe,
  widgetSites: widgetSitesDe,
  adminSpend: adminSpendDe,
  dataTasks: dataTasksDe,
  formFields: formFieldsDe,
};
