# DNS or certificate failure

**Alerts:** the uptime monitor fails with "DNS resolution" or TLS errors
while Render's dashboard shows the services healthy; the certificate
expiry monitor (under 21 days, `docs/operations/on-call.md`); owners
report the cabinet or the website chat "not secure" or not loading;
provider webhooks fail (Meta and Telegram cannot reach the API).

Every public host is a name at the registrar's DNS pointing at Render
(custom domains of `workshop-api` and `workshop-cabinet`); Render issues
and renews their certificates, which needs the DNS records to stay as
Render asked.

## Check

1. `dig +short <api host>` and `dig +short <cabinet host>` from two
   networks: no answer, a wrong target, or NXDOMAIN?
2. The registrar: is the domain expired, locked, or its name servers
   changed? The DNS host's status page (`docs/operations/contacts.md`).
3. Render → each service → Custom domains: "verified" and a certificate
   with a future expiry? A red domain means its record changed.
4. `openssl s_client -connect <host>:443 -servername <host>` shows the
   certificate's dates and issuer.

## Mitigate

- **Expired domain**: renew it at the registrar at once (founder); names
  come back as resolvers' caches expire (up to the records' TTL).
- **A record changed or deleted**: restore it from the zone file kept in
  the vault (`docs/operations/vendor-register.md`, exit plans), exactly as
  Render's custom domain page shows it.
- **DNS host down**: switch the domain's name servers to a second DNS host
  loaded with the same zone file; the registrar's change takes effect in
  minutes to hours.
- Tell owners through the status page's external copy (the uptime monitor's
  public page) if the cabinet's name is affected.

## Certificates

Render renews certificates by itself while the record points at it. A
certificate under 21 days means renewal failed: check step 3, fix the
record, then Render → Custom domains → verify again. Never put the API
behind a proxy that terminates TLS with its own certificate without
updating `FORWARDED_ALLOW_IPS` (`docker/entrypoint.sh`).

## Moving a name

To point a name at new hosts (a recovery elsewhere,
[render-outage](render-outage.md)): lower the record's TTL to 300 s a day
ahead when the move is planned, change the record, add the domain on the
new host, and wait for its certificate before telling owners.

## Afterwards

- Registrar auto-renew and the expiry monitor checked in the next access
  review; the zone file in the vault matches the live zone.
