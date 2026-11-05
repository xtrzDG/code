-- 1250_scheduled_audit_log_purge
--
-- The audit and security log is kept 1,095 days (docs/security/
-- data-classification.md, PRIV-07); the worker's daily
-- `purge_expired_audit_log` job removes what is older, chain by chain.
-- The application's roles may not call `workshop.purge_audit_chain`
-- (1193, 1200): it takes any cutoff past the 365-day floor. This file
-- adds `workshop.purge_expired_audit_chain(chain, created_before,
-- max_entries)`, which the platform role may call: it purges through
-- `workshop.purge_audit_chain` with the requested cutoff or the
-- retention's, whichever is older by the database's own clock, so the
-- platform role can only ever remove entries past the 1,095 days, the
-- way the scheduled job does. The operator's `workshop purge-audit-log`
-- keeps the function of 1193 with the migration role.
--
-- Online-safe (migrations/README.md): one transaction, a new function and
-- its grants; no table changes.

create or replace function workshop.purge_expired_audit_chain(
    target_chain text,
    created_before bigint,
    max_entries integer
)
returns bigint
language plpgsql
security definer
set search_path = pg_catalog
as $function$
declare
    -- The audit log's retention: 1,095 days in microseconds
    -- (app/utilities/compliance/audit_retention.py).
    retention constant bigint := 1095::bigint * 24 * 60 * 60 * 1000000;
    retention_cutoff bigint :=
        (extract(epoch from clock_timestamp()) * 1000000)::bigint - retention;
begin
    if created_before is null then
        raise exception 'a purge needs a cutoff'
            using errcode = 'invalid_parameter_value';
    end if;

    return workshop.purge_audit_chain(
        target_chain, least(created_before, retention_cutoff), max_entries
    );
end;
$function$;

comment on function workshop.purge_expired_audit_chain(text, bigint, integer) is
    'Purge one audit chain of the entries past the 1,095-day retention, never newer ones; the platform role''s daily job (1250).';

revoke all on function workshop.purge_expired_audit_chain(text, bigint, integer) from public;
grant execute on function workshop.purge_expired_audit_chain(text, bigint, integer)
    to workshop_platform;
