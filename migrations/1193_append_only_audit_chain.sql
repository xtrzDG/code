-- 1193_append_only_audit_chain
--
-- workshop:no-transaction
--
-- R13-AUDIT-TRAIL: the audit log becomes append-only and tamper-evident.
-- This file runs statement by statement outside a transaction (the header
-- above: its indexes on the busy audit table build CONCURRENTLY), so every
-- statement is idempotent and a failed try runs the file again.
--
-- Hash chains. Every entry the new release writes joins its business's
-- chain (or the platform's, `platform`, for entries that name no
-- business): `chain_key`, `chain_position`, `prev_hash` and `entry_hash`
-- (SHA-256 of its canonical JSON, app/utilities/compliance/
-- audit_chain_hashing.py). The application appends under the chain's
-- advisory lock (`hashtextextended('audit_chain|<chain>', 0)`), reading
-- the chain's newest entry and inserting the next one in one transaction;
-- the unique index below refuses a second entry at a position anyway.
-- Rows written before keep no chain fields and are never changed.
--
-- Append-only. A trigger refuses every UPDATE and DELETE of an entry with
-- insufficient_privilege, whoever runs it, except:
--   * an UPDATE of a VIEW entry that keeps it a VIEW under the same key is
--     skipped without an error and without a change: the previous release
--     counts a repeated view on the entry itself (an upsert), and keeps
--     doing so during the deploy and after a rollback; this release counts
--     repeated views in `audit_view_counts`, so a chained entry's hash
--     always holds;
--   * a DELETE inside `workshop.purge_audit_chain` (below).
-- The application's role (the owner of the tables until
-- W18-DB-ROLES-PASSKEYS gives the application a role of its own) loses
-- the DELETE and TRUNCATE privileges, and UPDATE on every column but the
-- three that the previous release's upsert (`insert ... on conflict do
-- update set business_id, document, updated_at`) names: Postgres checks
-- that privilege even when nothing conflicts, so without it every audited
-- request of the previous release would fail during the deploy and after
-- a rollback. The trigger refuses those updates too. The privileges move
-- in steps that never leave the owner without the three columns: they
-- are granted to PUBLIC first (no other role can reach the schema), then
-- the owner's table-wide UPDATE goes (which drops its column grants), the
-- columns are granted back to it, and PUBLIC loses them again.
--
-- Purges. `workshop.purge_audit_chain(chain, created_before, max_entries)`
-- removes the oldest entries of one chain (a prefix, up to the first entry
-- written at or after the cutoff, at most `max_entries`) and the chain's
-- entries from before the chain, under the chain's advisory lock, and
-- records the checkpoint `audit_chain_checkpoints` (the last removed
-- position and its hash), so the first entry left still links to it and
-- the chain stays verifiable. It runs with its owner's rights (the role
-- that ran this migration), which grants itself DELETE for the call when
-- it lacks it. Operators run it through `workshop purge-audit-log`.
--
-- Lookup columns (app/utilities/storage/document_lookup_catalog.py):
--   audit_log_entries     chain_key, chain_position  a chain's head and its
--                         check, the admin view of the platform's chain;
--                         security_event, entity_id  the failed sign-in
--                         checks per destination (platform alerts)
--   audit_chain_statuses  status                     broken chains (alert)
-- Rows written before this file have none of them (they are in no chain).
-- `doc_action` (1042) gets an index with the write time: the platform
-- alerts count the hour's exports, erasures and admin entries of every
-- business.

select workshop.add_lookup_column('audit_log_entries', 'chain_key', 'text');
select workshop.add_lookup_column('audit_log_entries', 'chain_position', 'bigint');
select workshop.add_lookup_column('audit_log_entries', 'security_event', 'text');
select workshop.add_lookup_column('audit_log_entries', 'entity_id', 'text');

select workshop.create_document_collection('audit_view_counts');
select workshop.create_document_collection('audit_chain_checkpoints');
select workshop.create_document_collection('audit_chain_statuses');
select workshop.add_lookup_column('audit_chain_statuses', 'status', 'text');

create or replace function workshop.keep_audit_log_append_only()
returns trigger
language plpgsql
set search_path = pg_catalog
as $function$
begin
    if tg_op = 'DELETE' then
        if current_setting('workshop.audit_chain_purge', true) = 'on' then
            return old;
        end if;

        raise exception 'audit log entries are kept; workshop.purge_audit_chain removes the oldest of a chain'
            using errcode = 'insufficient_privilege';
    end if;

    if old.document ->> 'action' = 'view'
        and new.document ->> 'action' = 'view'
        and new.document_key = old.document_key then
        -- The previous release counting a repeated view: the entry stays.
        return null;
    end if;

    raise exception 'audit log entries are append-only'
        using errcode = 'insufficient_privilege';
end;
$function$;

comment on function workshop.keep_audit_log_append_only() is
    'Refuse every change and deletion of an audit log entry (1193); a purge of a chain''s oldest entries deletes through workshop.purge_audit_chain.';

create or replace trigger audit_log_entries_append_only
    before update or delete on workshop.audit_log_entries
    for each row execute function workshop.keep_audit_log_append_only();

grant update (business_id, document, updated_at)
    on workshop.audit_log_entries to public;
revoke update, delete, truncate on workshop.audit_log_entries from current_user;
grant update (business_id, document, updated_at)
    on workshop.audit_log_entries to current_user;
revoke update (business_id, document, updated_at)
    on workshop.audit_log_entries from public;
revoke update, delete, truncate on workshop.audit_log_entries from public;

create or replace function workshop.purge_audit_chain(
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
    target_business text := case when target_chain = 'platform' then null else target_chain end;
    previous_through bigint;
    previous_purged bigint;
    first_created bigint;
    first_kept bigint;
    through bigint;
    through_hash text;
    removed bigint := 0;
    removed_unchained bigint := 0;
    purged_at bigint := (extract(epoch from clock_timestamp()) * 1000000)::bigint;
    granted boolean := false;
begin
    if target_chain !~ '^(platform|business_[0-9A-Za-z-]{1,70})$' then
        raise exception 'invalid audit chain: %', target_chain
            using errcode = 'invalid_parameter_value';
    end if;

    if max_entries is null or max_entries < 1 or created_before is null then
        raise exception 'a purge needs a cutoff and a positive batch size'
            using errcode = 'invalid_parameter_value';
    end if;

    perform pg_advisory_xact_lock(hashtextextended('audit_chain|' || target_chain, 0));

    select (document ->> 'through_position')::bigint,
           (document ->> 'purged_count')::bigint,
           created_at
      into previous_through, previous_purged, first_created
      from workshop.audit_chain_checkpoints
     where document_key = target_chain;

    select doc_chain_position into first_kept
      from workshop.audit_log_entries
     where doc_chain_key = target_chain and doc_created_at >= created_before
     order by doc_chain_position
     limit 1;

    select max(batch.doc_chain_position) into through
      from (
        select doc_chain_position
          from workshop.audit_log_entries
         where doc_chain_key = target_chain
           and doc_chain_position > coalesce(previous_through, 0)
           and (first_kept is null or doc_chain_position < first_kept)
         order by doc_chain_position
         limit max_entries
      ) as batch;

    if not has_table_privilege(current_user, 'workshop.audit_log_entries', 'DELETE') then
        execute format('grant delete on workshop.audit_log_entries to %I', current_user);
        granted := true;
    end if;

    perform set_config('workshop.audit_chain_purge', 'on', true);

    if through is not null then
        select document ->> 'entry_hash' into through_hash
          from workshop.audit_log_entries
         where doc_chain_key = target_chain and doc_chain_position = through;

        delete from workshop.audit_log_entries
         where doc_chain_key = target_chain and doc_chain_position <= through;
        get diagnostics removed = row_count;

        insert into workshop.audit_chain_checkpoints
            (document_key, business_id, document, created_at, updated_at)
        values (
            target_chain,
            target_business,
            jsonb_build_object(
                'schema_version', '1',
                'id', target_chain,
                'business_id', target_business,
                'through_position', through,
                'through_hash', through_hash,
                'purged_count', coalesce(previous_purged, 0) + removed,
                'created_at', coalesce(first_created, purged_at),
                'updated_at', purged_at
            ),
            coalesce(first_created, purged_at),
            purged_at
        )
        on conflict (document_key) do update
            set document = excluded.document, updated_at = excluded.updated_at;
    end if;

    -- Entries from before the chain (no chain fields) of the same log.
    if target_business is null then
        delete from workshop.audit_log_entries
         where document_key in (
            select document_key
              from workshop.audit_log_entries
             where business_id is null
               and doc_chain_key is null
               and doc_created_at < created_before
             limit max_entries
         );
    else
        delete from workshop.audit_log_entries
         where document_key in (
            select document_key
              from workshop.audit_log_entries
             where business_id = target_business
               and doc_chain_key is null
               and doc_created_at < created_before
             limit max_entries
         );
    end if;
    get diagnostics removed_unchained = row_count;

    perform set_config('workshop.audit_chain_purge', 'off', true);
    if granted then
        execute format('revoke delete on workshop.audit_log_entries from %I', current_user);
    end if;

    return removed + removed_unchained;
end;
$function$;

comment on function workshop.purge_audit_chain(text, bigint, integer) is
    'Remove the oldest entries of one audit chain before a cutoff and record its checkpoint (1193).';

revoke all on function workshop.purge_audit_chain(text, bigint, integer) from public;

create unique index concurrently if not exists audit_log_entries_doc_chain_idx
    on workshop.audit_log_entries (doc_chain_key, doc_chain_position);
create index concurrently if not exists audit_log_entries_doc_action_idx
    on workshop.audit_log_entries (doc_action, doc_created_at);
create index concurrently if not exists audit_chain_statuses_doc_status_idx
    on workshop.audit_chain_statuses (doc_status);
