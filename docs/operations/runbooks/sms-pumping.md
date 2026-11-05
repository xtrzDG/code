# SMS pumping and login floods

**Alert:** `otp_cap_trips` (SEV2): a platform-wide cap refused a login code
in the last 15-30 minutes. The platform admins also get one e-mail per cap
an hour (`PLATFORM_ADMIN_EMAILS`) and Sentry an event.

**Also:** the e-mail and Sentry warning "Sign-in codes sprayed: the
network … asked codes for …": one client network asked codes for 10 or
more different phones or e-mails within an hour (pumping, account
enumeration or a takeover attempt across accounts). It refuses nothing on
its own (`app/use_cases/users/otp_login/login_code_spray.py`).

## How it shows

- Login codes to many new numbers of one country or prefix, from few
  addresses; Twilio's spend rises.
- Real owners may be refused a code while a cap is full.

## Check

1. Which cap (the alert and the e-mail name it): per country
   (`OTP_SENDS_PER_COUNTRY_PER_HOUR`), new destinations
   (`OTP_SENDS_PER_HOUR`) or verified users
   (`OTP_SENDS_TO_VERIFIED_USERS_PER_HOUR`).
2. Twilio console → Monitor → Messaging logs: destinations, countries,
   cost of the last hour. Pumping looks like many premium or unusual
   prefixes in one country.
3. Logs and Sentry: the cap alert's warning names the cap, its hourly
   limit and the country; the API's access log shows whether the requests
   come from one network or many.
4. For a spray from one network: Admin → Audit (failed sign-in checks of
   that network) and the SMS provider's logs for the destinations it
   asked; whether any of them signed in afterwards.

## Mitigate

- Turn on the bot check if it is off: `TURNSTILE_SITE_KEY` and
  `TURNSTILE_SECRET_KEY` (risky requests must pass it).
- Add the abused country to `OTP_HIGH_RISK_COUNTRIES` (bot check always)
  or its prefixes to `OTP_DENIED_PHONE_PREFIXES` (never sent).
- Twilio → Messaging → Geo permissions: switch off countries the platform
  does not serve.
- Lower the country cap for the duration; real owners can still sign in by
  e-mail or Telegram.
- A spraying network: block it at the edge (the CDN or Render's network
  rules) for the duration; tell the owners of accounts it reached to
  check their devices (Account → Security, "Sign out everywhere").

## Afterwards

- Check Twilio's invoice for the period and ask Twilio support about
  fraudulent traffic refunds.
- Postmortem if the spend exceeded a day's normal SMS cost.
