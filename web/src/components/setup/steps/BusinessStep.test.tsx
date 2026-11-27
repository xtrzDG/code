import { fireEvent, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { NicheSummaryView, Schema, WizardQuestionView } from "@/api/types";
import { renderInLocale, textsIn } from "@/test/render";

import { BusinessStep, type BusinessForm } from "./BusinessStep";

vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh: vi.fn() }) }));

const SALON: NicheSummaryView = {
  key: "beauty",
  name: "Beauty salons",
  description: "",
  booking_unit: "time_slot",
  recommended_plans: [],
  requires_legal_review: false,
  resource_kind: "staff",
  resource_noun: "master",
  takes_bookings: true,
  typical_check: null,
  wave: "a",
} as unknown as NicheSummaryView;

/** The salon's required question about the business: which services it offers. */
const SERVICES: WizardQuestionView = {
  question: {
    key: "services",
    fact_key: "services",
    step: "niche_and_languages",
    answer_type: "multiple_choice",
    is_required: true,
    label: "Which services do you offer?",
    hint: null,
    choices: [{ key: "hair", label: "Hair" }],
  } as Schema<"LocalizedQuestionView">,
};

const FORM: BusinessForm = { name: "Salon Aurora", nicheKey: "beauty", answers: {} };

function renderStep(questions: readonly WizardQuestionView[] | null, onSubmit = vi.fn()) {
  const step = (asked: readonly WizardQuestionView[] | null) => (
    <BusinessStep
      form={FORM}
      onChange={vi.fn()}
      niches={{ data: [SALON], error: null, reload: vi.fn() }}
      questions={asked}
      isNicheFixed={false}
      onSubmit={onSubmit}
    />
  );
  const view = renderInLocale(step(questions));
  return { ...view, onSubmit, rerenderWith: (asked: readonly WizardQuestionView[] | null) => view.rerender(step(asked)) };
}

describe("BusinessStep: Continue while the chosen kind's questions load", () => {
  const { t } = textsIn("en");
  const continueButton = () => screen.getByRole<HTMLButtonElement>("button", { name: t("tunnel.continue") });

  it("waits, disabled, until the questions are there, then checks them", () => {
    const { onSubmit, rerenderWith } = renderStep(null);

    // Pressed now it would check nothing and say nothing.
    expect(continueButton().disabled).toBe(true);
    fireEvent.click(continueButton());
    expect(onSubmit).not.toHaveBeenCalled();

    rerenderWith([SERVICES]);
    expect(continueButton().disabled).toBe(false);
    fireEvent.click(continueButton());
    expect(screen.getAllByText(t("validation.required"))).toHaveLength(1);
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("is not held back before a kind is chosen: it says what is missing", () => {
    const onSubmit = vi.fn();
    renderInLocale(
      <BusinessStep
        form={{ name: "", nicheKey: "", answers: {} }}
        onChange={vi.fn()}
        niches={{ data: [SALON], error: null, reload: vi.fn() }}
        questions={[]}
        isNicheFixed={false}
        onSubmit={onSubmit}
      />,
    );

    expect(continueButton().disabled).toBe(false);
    fireEvent.click(continueButton());
    expect(screen.getAllByText(t("tunnelBusiness.business.errors.name"))).toHaveLength(1);
    expect(screen.getAllByText(t("tunnelBusiness.business.errors.kind"))).toHaveLength(1);
    expect(onSubmit).not.toHaveBeenCalled();
  });
});
