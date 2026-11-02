# WhatsApp number and template quality

**Alert:** `whatsapp_quality` (SEV2): Meta warned about a business's
WhatsApp number or one of its templates, the step before a restriction
(a lower messaging limit, a paused template, a banned number):

- the number was flagged or its messaging limit lowered
  (`phone_number_quality_update` FLAGGED or DOWNGRADE);
- a template's quality fell to yellow or red
  (`message_template_quality_update`);
- a template was paused, disabled or flagged
  (`message_template_status_update`);
- a template was moved into the MARKETING category
  (`template_category_update`). A service message (a text-back, a
  reminder, a confirmation, a staff reply) must not go as a marketing
  template, and a marketing template may only reach customers who gave
  marketing consent.

The WhatsApp webhook logs each warning ("WhatsApp quality warning: ...")
with the number's event or the template's name and language, and counts
one platform signal each (`report_quality_warnings`).

## Check

1. Which number or template? Search the API logs for "WhatsApp quality
   warning"; the webhook's phone number id names the business's channel.
2. In Meta Business Manager (WhatsApp Manager → Insights and Message
   templates): the number's quality rating and messaging limit, the
   template's quality, status and category.
3. What was sent with it? The client's outbox for the template's name:
   text-backs (Settings → Calls), reminders and confirmations, campaigns.

## Mitigate and fix

- A template moved to MARKETING that a service message uses: ask the
  owner to register a utility template without promotional words and
  name it in the settings (Settings → Calls for text-backs); until then
  turn the text-back's WhatsApp leg off. The platform's own templates
  (`WHATSAPP_*_TEMPLATE_NAME`) are fixed by the operator the same way.
- A template whose quality fell or that was paused: customers block or
  report it; review its wording with the owner and stop the campaign that
  uses it.
- A flagged or downgraded number: pause the client's campaigns, check
  that only opted-in customers get marketing, and contact the owner.

## Afterwards

Record the warning, the template and the change in the incident record;
audit the business's templates by category in Meta Business Manager.
