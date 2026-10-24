/**
 * How a screen of "Create an AI assistant" is shown. `tunnel`: one step of
 * the full-screen setup ("Step 3 of 8", the big question, Back and
 * Continue). `edit`: the same screen inside Assistant → Business profile
 * for a live business, without a step counter or the way on, saving
 * every change by itself.
 */
export type StepMode = "tunnel" | "edit";
