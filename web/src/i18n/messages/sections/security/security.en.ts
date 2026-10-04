/**
 * `security.*` texts: Account → Security (the authenticator app, recovery
 * codes, how this session is signed in) and a business's two-factor
 * requirement in Settings → Team, in English: the reference that ru and ka
 * are typed against.
 */

export const securityEn = {
  title: "Security",
  description: "How you sign in to the cabinet.",
  menu: "Security",
  required: {
    business:
      "This business asks everyone in its team to sign in with an authenticator app. Set one up below, then continue.",
    admin:
      "The admin pages need a sign-in with an authenticator app. Set one up below, or confirm with it, then continue.",
    continue: "Continue",
  },
  app: {
    title: "Authenticator app",
    description:
      "After the login code, the cabinet also asks for a code from an app on your phone. Someone who gets your login code still cannot get in.",
    on: "On",
    off: "Off",
    pending: "Setup not finished",
    since: "Turned on {date}",
    lastUsed: "Last code {date}",
    setUp: "Set up",
    finishSetup: "Finish the setup",
    remove: "Turn off",
    removeTitle: "Turn off the authenticator app?",
    removeDescription:
      "Signing in will only ask for the login code again, and your recovery codes stop working.",
    removeAdmin:
      "As a platform admin you will be asked to set it up again at the next sign-in.",
    removed: "The authenticator app is off",
    adminRequired: "Platform admins always sign in with an authenticator app.",
    turnedOn: "The authenticator app is on",
  },
  codes: {
    title: "Recovery codes",
    description: "For a lost phone: each code replaces the app's code once.",
    left: {
      one: "{count} unused code left",
      other: "{count} unused codes left",
    },
    none: "No unused codes left. Get new ones.",
    renew: "Get new codes",
    renewTitle: "Get new recovery codes?",
    renewDescription: "Your current codes stop working at once.",
    renewing: "Preparing…",
  },
  session: {
    title: "This session",
    twoFactor: "Signed in with a login code and the authenticator app.",
    oneFactor: "Signed in with a login code only.",
    upgrade: "Confirm with the app",
    upgraded: "This session now counts as signed in with the app",
  },
  team: {
    title: "Two-factor sign-in for the team",
    description:
      "Everyone who opens this business must sign in with an authenticator app as well as the login code.",
    toggle: "Require an authenticator app",
    on: "Required for everyone",
    off: "Not required",
    without: {
      one: "{count} person has no authenticator app yet: they cannot open the business until they set one up in Account → Security.",
      other:
        "{count} people have no authenticator app yet: they cannot open the business until they set one up in Account → Security.",
    },
    everyone: "Everyone has an authenticator app.",
    ownFirst:
      "Set up your own authenticator app first: open Account → Security.",
    openSecurity: "Open Security",
    ownerOnly: "Only an owner can change this.",
    saved: "Saved",
  },
} as const;
