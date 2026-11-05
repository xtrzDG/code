/**
 * Settings → General's assistant controls (an owner's kill switches): pass
 * every customer to the team, and the actions the assistant may take. The
 * backend refuses a switched-off action whenever the model asks for it.
 */

import type { MessageKey } from "@/i18n/translate";

import type { AssistantSettingsBody, AssistantSettingsView } from "./customerMemory";

/** The actions an owner may switch off, in the order the card lists them (as the backend's SWITCHABLE_TOOLS). */
export const SWITCHABLE_ACTIONS = [
  "create_booking",
  "reschedule_booking",
  "cancel_booking",
  "join_waitlist",
  "create_lead",
  "send_link",
  "send_payment_link",
] as const;

export type SwitchableAction = (typeof SWITCHABLE_ACTIONS)[number];

export interface AssistantControls {
  isHandedOver: boolean;
  disabledActions: SwitchableAction[];
}

function isSwitchable(tool: string): tool is SwitchableAction {
  return (SWITCHABLE_ACTIONS as readonly string[]).includes(tool);
}

export function assistantControls(view: AssistantSettingsView): AssistantControls {
  return {
    isHandedOver: view.is_paused,
    disabledActions: (view.disabled_tools ?? []).filter(isSwitchable),
  };
}

/** The action switched on or off, in the card's order. */
export function withAction(disabled: SwitchableAction[], action: SwitchableAction, isOn: boolean): SwitchableAction[] {
  const next = new Set(disabled);
  if (isOn) {
    next.delete(action);
  } else {
    next.add(action);
  }
  return SWITCHABLE_ACTIONS.filter((candidate) => next.has(candidate));
}

/** The whole settings with the controls changed: the memory switches are sent as stored (a PUT replaces them). */
export function controlsBody(view: AssistantSettingsView, controls: AssistantControls): AssistantSettingsBody {
  return {
    remembers_customers: view.remembers_customers,
    shares_team_notes: view.shares_team_notes,
    is_paused: controls.isHandedOver,
    disabled_tools: controls.disabledActions,
  };
}

/** The toast after a saved change: what is different now. */
export function controlsChangeText(before: AssistantControls, after: AssistantControls): MessageKey | null {
  if (before.isHandedOver !== after.isHandedOver) {
    return after.isHandedOver ? "assistantControls.handedOver" : "assistantControls.resumed";
  }
  if (after.disabledActions.length > before.disabledActions.length) {
    return "assistantControls.actionOff";
  }
  if (after.disabledActions.length < before.disabledActions.length) {
    return "assistantControls.actionOn";
  }
  return null;
}

export function actionLabel(action: SwitchableAction): MessageKey {
  return `assistantControls.actions.${action}`;
}
