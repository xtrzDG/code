# A campaign held over its opt-out rate

**Alert:** `campaign_opt_outs` (SEV3): the hourly campaign job held a
business's return-visit campaign for review. Of the customers its messages
of the last 30 days reached, 5 % or more (and at least 3 of at least 40)
asked for no more messages since: a STOP in the chat the message went to,
or their marketing consent taken back. Messaging providers treat such a
rate as spam (Gmail and Yahoo bulk-sender rules, WhatsApp quality
ratings), and the platform's numbers and templates carry the cost. The
held campaign sends nothing; its owners were told why in their language
(their sign-in e-mail, else an SMS to their sign-in phone). The owner's
settings stay as they are.

## Check

1. Which business? `GET /v1/admin/campaign-holds` lists every held
   campaign with the time and the figures (customers reached, opt-outs);
   the worker's warning line names the business too.
2. Open the client: what does the campaign write (Bookings → Return
   visits of the business, through "Open cabinet"), to whom (all
   customers or a segment), and how often? Did the customers give
   marketing consent?
3. Look at the business's WhatsApp quality rating and recent
   `whatsapp_quality` alerts.

## Mitigate and fix

- Spam or bought lists: keep the hold, suspend the client if the terms
  were broken, and keep the evidence.
- A real business with a clumsy message or audience: agree with the owner
  on a narrower audience (a segment of customers who gave consent) or a
  longer delay, then release the hold with
  `POST /v1/admin/campaign-holds/{business_id}/release` and the reason
  (SUPER admins). The release is audited and the owners are
  told that their campaign writes again. From the release on, the
  campaign's rate counts only the messages sent after it: the messages
  that held it cannot hold it again, and the campaign is held again only
  when 5 % of at least 40 customers it writes to from then on opt out.

## Afterwards

Nothing resolves the hold by itself: a held campaign stays held until an
admin releases it. Record the business, the figures and the decision in
the incident record.
