# Meta App Review: what to submit and how to show it

This pack holds the texts and screencast scripts for the platform's Meta
app, so that Meta can review WhatsApp, Messenger and Instagram access. Meta
reviews the app in English, so this page is in English. The setup itself
(app, webhook, variables) is in `docs/LAUNCH.md`, section 4.5. Until Meta
approves the permissions below, "Continue with Facebook" works only for
people with a role on the app (admins, developers, testers).

## Before you submit

Have all of this ready, in this order:

1. **Business verification** of the platform's business portfolio
   (business.facebook.com → Security Center). Meta asks for company
   documents. Tech Provider status for WhatsApp needs it as well.
2. **The production site is live**, with final legal texts. The privacy
   policy and terms must not contain bracketed placeholders, because Meta
   opens these addresses during review (`docs/LAUNCH.md`, "Блокер запуска:
   юридические тексты").
3. **App settings → Basic:**
   - App domains: the site's domain.
   - Privacy Policy URL: `https://<site>/en/privacy`.
   - Terms of Service URL: `https://<site>/en/terms`.
   - User data deletion: choose "Data deletion instructions URL" and point it
     at `https://<site>/en/privacy`, section "8. Your rights". It says how
     people ask for their data to be deleted.
   - App icon 1024 × 1024, category "Business and pages", and a contact
     e-mail.
4. **Webhook** set and verified: `<api>/v1/channels/meta/webhook` with
   `META_VERIFY_TOKEN`, subscribed to the fields listed in
   `docs/LAUNCH.md`, section 4.5.
5. **Facebook Login for Business:**
   - The cabinet's domain is listed under "Allowed Domains for the
     JavaScript SDK".
   - A configuration of the WhatsApp Embedded Signup variant exists, with a
     system-user token and the two WhatsApp permissions
     (`META_EMBEDDED_SIGNUP_CONFIG_ID`).
6. **A review account the reviewers can sign in with.** The cabinet signs
   in with one-time codes and has no passwords.
   - Create a mailbox used only for review, for example a new Gmail
     address.
   - Create a business with it in the cabinet: a published assistant and a
     few facts, so it answers sensibly.
   - Give the mailbox's address and password in the review form's test
     instructions. Reviewers sign in with that address and read the code in
     the mailbox.
   - Delete the mailbox's access once review ends.
7. **Test assets connected to the review business:** a Facebook page, an
   Instagram professional account linked to that page, and a WhatsApp test
   number. They make the screencasts and the reviewers' own tests possible.

## Permissions: what to write in "How will your app use this permission?"

The app version the cabinet and the server use is Graph API `v23.0`
(`app/utilities/channels/meta_sign_in.py`). Ask for advanced access to each
permission below. Each text is meant to be pasted as it stands; replace
`<site>` with the real address.

**whatsapp_business_management**
> Business owners connect their own WhatsApp Business number to our AI front-desk assistant with WhatsApp Embedded Signup ("Continue with Facebook" on the Channels page of our cabinet). We use this permission to read the WhatsApp Business Account and phone number the owner shared in the signup window, to register that number with the Cloud API, to subscribe our app to that account's webhooks (messages, number quality, template status), and to read the names, categories and statuses of the account's message templates. We never create accounts or numbers the owner did not choose, and we only act on the accounts the owner shared.

**whatsapp_business_messaging**
> Our assistant answers the messages that customers send to the business's WhatsApp number: it replies to questions, takes bookings and hands the conversation to the business's staff when needed. Staff can also reply themselves from the Inbox of our cabinet. Outside the 24-hour customer service window we only send the business's approved template messages, such as booking confirmations and reminders for a booking the customer made.

**pages_show_list**
> After signing in with Facebook, the business owner sees the list of Facebook Pages they manage and picks the page whose Messenger chats (and linked Instagram account) the assistant should answer. We only show the list to the owner; we store only the page the owner picked.

**pages_messaging**
> Our assistant replies to the messages customers send to the business's Facebook Page in Messenger: answers, bookings and handovers to staff. Staff can reply themselves from the Inbox of our cabinet. Messages are sent only in reply to a customer's conversation.

**pages_manage_metadata**
> When the owner connects a page, we subscribe our app to that page's webhooks (messages and Instagram events), so that new customer messages reach the assistant. Without this the assistant would never see the page's messages.

**business_management**
> Many businesses own their Facebook Page and Instagram account through a business portfolio rather than personally. We use this permission during "Continue with Facebook" to find the pages and accounts that belong to the business portfolio the owner chose, so the owner can connect them. We do not change the portfolio, its people or its assets.

**instagram_basic**
> For the page the owner picks, we read the linked Instagram professional account's id and username. We show the username in the page picker ("Instagram: @username") so the owner can tell which account they connect, and we use the id to receive and send that account's Direct messages.

**instagram_manage_messages**
> Our assistant replies to the Direct messages customers send to the business's Instagram professional account: answers, bookings and handovers to staff. Staff can reply themselves from the Inbox of our cabinet. Messages are sent only in reply to a customer's conversation.

**instagram_manage_comments**
> The owner can switch on "Replies to comments" and set keywords (for example "menu" or "price"). When someone writes a keyword in a comment under the business's post, the assistant sends that person one private reply in Direct. It sends at most one a day to each person and 60 an hour per account. We read the comments of the connected account only to find these keywords.

## Screencasts

Record each one in English, at full screen, with the cabinet in English.
Show the address bar so the reviewer sees the real site. Each screencast
must show the user granting the permission in Meta's own window, and then
the product using it. Keep each one under about three minutes.

**1. WhatsApp (whatsapp_business_management, whatsapp_business_messaging)**

1. Sign in to the cabinet with the review account. Open the review
   business, then Assistant → Channels.
2. On the WhatsApp card, press "Continue with Facebook". Facebook's window
   opens: sign in, choose the test WhatsApp Business account and number,
   and accept the permissions. Keep the permission screen visible for a
   moment.
3. Back in the cabinet the WhatsApp card shows as connected, with the
   number.
4. On a phone, send the business's number a message, for example "Are you
   open on Sunday?". Show the assistant's reply arriving on the phone.
5. Open the Inbox in the cabinet. Show the same conversation, then type a
   reply as staff and press "Send". Show it arriving on the phone.

**2. Messenger (pages_show_list, pages_manage_metadata, business_management, pages_messaging)**

1. Assistant → Channels → Messenger card → "Continue with Facebook".
2. In Facebook's window, tick the test page and accept the permissions.
3. The cabinet shows "Choose a page" with the pages you manage. Pick the
   test page and press "Connect this page". The card shows as connected.
4. From another Facebook account, message the page in Messenger. Show the
   assistant's reply.
5. In the Inbox, reply as staff and show it arriving in Messenger.

**3. Instagram (instagram_basic, instagram_manage_messages, instagram_manage_comments)**

1. Assistant → Channels → Instagram card → "Continue with Facebook". In
   Facebook's window, tick the page linked to the test Instagram
   professional account.
2. The page picker shows "Instagram: @username" next to the page. Connect
   it.
3. From another Instagram account, send the business account a Direct
   message. Show the assistant's reply, then reply from the cabinet's Inbox.
4. On the Instagram card, open "Replies to comments", switch on "Reply in
   Direct to comments with a keyword" and add a keyword. From the other
   account, comment that keyword under one of the business's posts. Show the
   single Direct message that arrives.

## After approval

- Request Tech Provider status for WhatsApp (needs business verification).
  Until then only numbers of businesses that people with a role on the app
  connect can be used.
- Switch the app to Live mode.
- Set `META_APP_ID`, `META_APP_SECRET`, `META_VERIFY_TOKEN` and
  `META_EMBEDDED_SIGNUP_CONFIG_ID` on production (`docs/LAUNCH.md`,
  section 4.5) if they are not set yet. Then connect a real business's
  WhatsApp from the cabinet and check that a message gets an answer.
- If Meta rejects a permission, its message names what it did not see.
  Re-record that screencast to show exactly that, and submit again.
