/**
 * `coachMarks.*` texts: the one-time tips on the Inbox, the Assistant's test
 * page and Channels, in English: the reference that ru and ka are typed
 * against.
 */

export const coachMarksEn = {
  label: "Tip",
  gotIt: "Got it",
  readGuide: "Read the guide",
  inbox: {
    title: "Your team inbox",
    body: "Conversations that need a person come first. Open one to reply, give it to a colleague or leave a note only the team sees.",
  },
  assistant: {
    title: "Try your assistant here first",
    body: "Write as a customer would. What you teach the assistant shows up here before customers get it.",
  },
  channels: {
    title: "Connect where your customers write",
    body: "Start with the channel your customers use most. Each card says whether it works and when the last message came in.",
  },
} as const;
