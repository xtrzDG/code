/**
 * Named types of the backend API, generated from openapi.json.
 *
 * Use `Schema<"BookingView">` for any response model, or the aliases below.
 * Request bodies are inline in `paths`; take them with `RequestBody<...>`.
 * Regenerate with `npm run gen:api` after the backend changes.
 */

import type { components, operations, paths } from "./schema";

export type { components, operations, paths };

export type Schemas = components["schemas"];

/** A response model of the API by its name: `Schema<"BusinessView">`. */
export type Schema<Name extends keyof Schemas> = Schemas[Name];

type JsonBody<Operation> = Operation extends {
  requestBody?: { content: { "application/json": infer Body } };
}
  ? Body
  : never;

/**
 * The JSON body of an operation:
 * `RequestBody<"/v1/businesses", "post">` is the create-business body.
 */
export type RequestBody<
  Path extends keyof paths,
  Method extends "post" | "put" | "patch" | "delete",
> = JsonBody<NonNullable<paths[Path][Method]>>;

// Accounts and catalog
export type UserView = Schema<"UserView">;
export type CurrentUserView = Schema<"CurrentUserView">;
export type UserMembershipView = Schema<"UserMembershipView">;
export type OtpChallengeView = Schema<"OtpChallengeView">;
export type LoginSessionView = Schema<"LoginSessionView">;
export type CountryListItem = Schema<"CountryListItem">;
export type CountryProfileView = Schema<"CountryProfileView">;
export type LanguageOption = Schema<"LanguageOption">;
export type NicheSummaryView = Schema<"NicheSummaryView">;
export type OtpDeliveryChannel = Schema<"OtpDeliveryChannel">;

// Businesses
export type BusinessView = Schema<"BusinessView">;
export type BusinessStatus = Schema<"BusinessStatus">;
export type BusinessMemberRole = Schema<"BusinessMemberRole">;
export type NicheKey = Schema<"NicheKey">;

// Profile wizard
export type ProfileWizardView = Schema<"ProfileWizardView">;
export type ProfileWizardStep = Schema<"ProfileWizardStep">;
export type WizardStepView = Schema<"WizardStepView">;
export type WizardQuestionView = Schema<"WizardQuestionView">;
export type QuestionAnswerType = Schema<"QuestionAnswerType">;
export type BusinessProfileView = Schema<"BusinessProfileView">;
export type OpeningInterval = Schema<"OpeningInterval">;
export type Weekday = Schema<"Weekday">;
export type ProfileGapsView = Schema<"ProfileGapsView">;
export type ProfileGap = Schema<"ProfileGap">;
export type KnowledgeItemDetails = Schema<"KnowledgeItemDetails">;
export type KnowledgeItemKind = Schema<"KnowledgeItemKind">;
export type ResourceKind = Schema<"ResourceKind">;
export type BusinessLinkKind = Schema<"BusinessLinkKind">;

/** Body of `PUT /v1/businesses/{business_id}/profile/steps/{step}` (union of the six steps). */
export type ProfileStepBody = RequestBody<
  "/v1/businesses/{business_id}/profile/steps/{step}",
  "put"
>;

// Two-factor sign-in and step-up
export type AuthLevel = Schema<"AuthLevel">;
export type MfaRequiredView = Schema<"MfaRequiredView">;
export type MfaChallengeView = Schema<"MfaChallengeView">;
export type TotpEnrollmentView = Schema<"TotpEnrollmentView">;
export type RecoveryCodesView = Schema<"RecoveryCodesView">;
export type AccountSecurityView = Schema<"AccountSecurityView">;
export type StepUpChallengeView = Schema<"StepUpChallengeView">;
export type SessionAssuranceView = Schema<"SessionAssuranceView">;
export type BusinessSecurityView = Schema<"BusinessSecurityView">;

// Devices, the platform admin team and support access
export type UserSessionView = Schema<"UserSessionView">;
export type SessionDevice = Schema<"SessionDevice">;
export type PlatformAdminView = Schema<"PlatformAdminView">;
export type PlatformAdminRole = Schema<"PlatformAdminRole">;
export type PlatformAdminPermission = Schema<"PlatformAdminPermission">;
export type SupportAccessView = Schema<"SupportAccessView">;
export type SupportSessionView = Schema<"SupportSessionView">;
