/**
 * `widgetSites.*` texts: Channels → Website chat → the websites allowed to
 * show the chat, in English: the reference that ru and ka are typed
 * against.
 */

export const widgetSitesEn = {
  title: "Websites that may show the chat",
  description:
    "The chat's code works on any website it is pasted on. List your own sites and the chat works only there, so nobody can run your assistant, and your plan, from a copy of the code.",
  anySite: "Any website",
  sites: { one: "{count} website", other: "{count} websites" },
  listLabel: "Allowed websites",
  empty: "No list yet: the chat works on any website.",
  addLabel: "Website address",
  addHint: "As in the browser's address bar. The www. address and http or https count as the same site.",
  placeholder: "https://cafe-batumi.ge",
  add: "Add",
  remove: "Remove {site}",
  invalid: "This is not a website address. Type it as in the browser's address bar, for example cafe-batumi.ge.",
  duplicate: "This website is already on the list.",
  full: "The list holds up to {count} websites.",
  alwaysAllowed: "Your chat page and the preview in this cabinet always work.",
  ownerOnly: "Only an owner can change this list.",
  save: "Save list",
  saving: "Saving…",
  unsaved: "Not saved",
  savedToast: "Website list saved",
  clearedToast: "The chat works on any website again",
} as const;
