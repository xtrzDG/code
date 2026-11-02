# Mass bookings and mass cancellations

**Alerts:**

- `booking_spike` (SEV3): a business got more than 40 new bookings in an
  hour. A script or a competitor may be holding every slot with fake
  bookings (OWASP OAT-021, denial of inventory).
- `cancellation_spike` (SEV3): more than 15 bookings of one business were
  cancelled in an hour: a mass cancellation by someone with the booking
  links, a deposit sweep releasing many unpaid holds, or the owner
  closing for a day.

Every booking change the platform announces is counted per business and
hour (`BookingSurgeObserverFacilitator`); the alert fires once per
business and hour, and a warning line of the API or the worker names the
business ("had more than 40 new bookings this hour"). Owners' test chats
never count. Nothing is refused by this alert: the booking caps
(5 a day per contact, 10 a day per client network and 200 a day per
business for anonymous bookings, `booking_limits.py`) do the refusing.

## Check

1. Which business? Search the logs for "new bookings this hour" or
   "cancellations this hour" with its `business_id`; open the client on
   Admin → Clients.
2. Where do the bookings come from? Their source channel and contacts in
   the client's bookings: many web chat or phone bookings from new
   contacts with similar names are fake; bookings staff entered in the
   cabinet, or a busy evening of real customers, are not.
3. For cancellations: the client's audit log shows who cancelled (staff,
   the customer's link, the deposit sweep). A deposit sweep of lapsed holds
   means the holds were never paid: the same fake-booking pattern.

## Mitigate and fix

- Fake bookings: ask the owner to block the contacts (Customers, the
  customer, "Block this customer") and cancel the fake bookings; pause the client's assistant on
  Admin → Clients while it lasts. Suggest a deposit above a party size
  (Settings → Deposits) so a held table costs the holder something.
- A mass cancellation the owner did not make: rotate the affected
  bookings' links by contacting the owner, and treat a leak of links as a
  possible data breach ([data-breach](data-breach.md)).
- A legitimate busy business or a planned closure: nothing to do; note it
  in the incident record so the next alert of the client is read in that
  light.

## Afterwards

The alert resolves once the windows are quiet. Record the business, the
pattern and the counts in the incident record; a repeated pattern is a
reason to lower the booking caps.
