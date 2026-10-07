/**
 * `adminTeam.*` texts of the platform admin team page (/admin/team): who
 * may open the admin pages, with which role, adding and removing people,
 * in English: the reference that ru and ka are typed against.
 */

export const adminTeamEn = {
  nav: "Team",
  title: "Admin team",
  description:
    "Who may open the admin pages and what each role may do. Every change is written to the audit log.",
  roles: {
    super: "Super admin",
    support_readonly: "Support (read only)",
    billing: "Billing",
  },
  roleHints: {
    super: "Everything: clients, operations, metrics, the team; changes in a client's cabinet when the owner allows them.",
    support_readonly: "Clients and the platform's health; opens a client's cabinet for an hour, read only.",
    billing: "Clients, their account (trial, discounts, credit, payments by hand, plan), notes and the growth metrics; never opens a client's cabinet.",
  },
  you: "You",
  notSignedIn: "Has not signed in yet",
  addedBy: "Added by {name} {date}",
  addedOn: "Added on the Team page {date}",
  bootstrapped: "From the PLATFORM_ADMIN_* lists {date}",
  role: "Role",
  roleFor: "Role of {name}",
  changed: "Role changed",
  remove: "Remove",
  removeLabel: "Remove {name} from the team",
  removeTitle: "Remove {name} from the admin team?",
  removeDescription: "They lose the admin pages at their next request.",
  removed: "Removed from the team",
  add: "Add a person",
  addTitle: "Add a person to the admin team",
  addDescription:
    "They get the admin pages the next time they sign in with this phone number or e-mail, and must set up an authenticator app.",
  by: "Signs in with",
  byPhone: "Phone number",
  byEmail: "E-mail",
  phone: "Phone number",
  email: "E-mail",
  added: "Added to the team",
  lastSuper: "The team needs at least one super admin: give the role to someone else first.",
} as const;
