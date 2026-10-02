import type {
  KnowledgeItemDetails,
  ProfileStepBody,
  ProfileWizardView,
  Schema,
  WizardStepView,
} from "@/api/types";

export type ProfileStepSaveResult = Schema<"ProfileStepSaveResult">;

/** What every wizard step component receives from OnboardingWizard. */
export interface StepProps {
  wizard: ProfileWizardView;
  step: WizardStepView;
  /** Knowledge items of the business (offer and FAQ steps); undefined while loading. */
  knowledge: KnowledgeItemDetails[] | undefined;
  /** Only owners may change the profile; staff see it read-only. */
  canEdit: boolean;
  isSaving: boolean;
  isLastStep: boolean;
  /** PUT …/profile/steps/{step}; resolves to the result, or null on failure (already shown). */
  onSave: (body: ProfileStepBody, options: { advance: boolean }) => Promise<ProfileStepSaveResult | null>;
  /** Tell the wizard that the form has unsaved changes. */
  onChange: () => void;
  /** Reload step completion and "what to add" after a change saved outside the step form. */
  onProgressChanged: () => void;
}
