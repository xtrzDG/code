-- 1200_tenant_and_platform_roles
--
-- W18-DB-ROLES-PASSKEYS: tenant isolation stops depending on a setting the
-- application could switch off itself. Every policy read
--     business_id = current_setting('app.business_id', true)
--     or current_setting('app.bypass_rls', true) = 'on'
-- and the application connected with one role, so one SQL injection (or a
-- wrong platform-wide scope) could `set app.bypass_rls = 'on'` and read
-- every business. From here on no policy reads that setting; what a
-- session sees follows the role it logs in with:
--   workshop_tenant    group (NOLOGIN) of the tenant pool's login role
--                      (DATABASE_URL_TENANT): the rows of the business in
--                      app.business_id, whatever else a session sets.
--                      Never BYPASSRLS nor superuser (refused below).
--   workshop_platform  group of the platform pool's login role
--                      (DATABASE_URL_PLATFORM): every row, through the
--                      `platform_access` policies (BYPASSRLS is not
--                      inherited from a group, and managed Postgres keeps
--                      it from its users).
--   the table owner    the migration role (DATABASE_URL): migrations,
--                      backups, the restore drill, maintenance commands.
--                      It joins workshop_platform, so the previous
--                      release, which connects as the owner and sets
--                      app.bypass_rls, keeps reading every row during the
--                      deploy and after a rollback.
-- Creating the groups needs CREATEROLE once; without it an administrator
-- creates them (and the login roles) before the deploy, as
-- docs/operations/deploys.md "Database roles" shows. The policies name
-- only the groups, so a dump restores on any server that has them.
--
-- Every table under row-level security gets `tenant_isolation` (to
-- workshop_tenant) and `platform_access` (to workshop_platform) in place
-- of `business_isolation` (`workshop.apply_role_policies`), and so do new
-- collections (`workshop.create_document_collection`). Both groups may
-- select, insert, update and delete in every workshop table (default
-- privileges cover later tables), except: `schema_migrations` is
-- read-only; `audit_log_entries` (append-only since 1193) takes select
-- and insert only, the grants 1193 left to the application's role moving
-- to the groups without UPDATE (the owner keeps its three UPDATE columns
-- for the previous release until the release after this one); and the
-- tables whose rows never name a business (people, their sessions and
-- factors, the platform's own operations: the list below) are the
-- platform's alone, so a statement smuggled into a business's request
-- cannot add a row there (a user, a platform admin) that platform code
-- would trust. Later migrations create such a collection with
-- `workshop.create_platform_collection('name')`. Neither group may call
-- the migration helpers or `workshop.purge_audit_chain`; the request rate
-- limits (`workshop.count_request_within_limits`) run on the platform pool.
--
-- Online: one transaction, so the previous release never sees half the
-- policies changed; each policy change locks its table for a moment, and
-- a table kept busy past the runner's lock_timeout rolls the try back to
-- run again later (migrations/README.md).
--
-- Reversible: `select workshop.revert_tenant_and_platform_roles()` (as the
-- owner, with this release stopped) restores every `business_isolation`
-- policy, takes the groups' privileges away and removes this file's
-- record, so the previous release runs as before and the next `workshop
-- migrate` applies this file again (deploys.md "Rolling back past 1200").
-- The owner stays in workshop_platform, which then no policy names.

do $roles$
begin
    if not exists (select from pg_catalog.pg_roles where rolname = 'workshop_tenant') then
        create role workshop_tenant nologin nosuperuser nobypassrls;
    end if;
    if not exists (select from pg_catalog.pg_roles where rolname = 'workshop_platform') then
        create role workshop_platform nologin nosuperuser;
    end if;
exception
    -- Roles belong to the server: another database of it may have created
    -- them a moment ago.
    when duplicate_object then
        null;
    when insufficient_privilege then
        raise exception 'creating the roles workshop_tenant and workshop_platform needs CREATEROLE'
            using errcode = 'insufficient_privilege',
                  hint = 'As an administrator, run once: create role workshop_tenant nologin; '
                      'create role workshop_platform nologin; grant workshop_platform to '
                      'the migration role; then deploy again '
                      '(docs/operations/deploys.md, "Database roles").';
end;
$roles$;

do $owner$
begin
    if exists (select from pg_catalog.pg_roles
                where rolname = 'workshop_tenant' and (rolsuper or rolbypassrls)) then
        raise exception 'workshop_tenant must be neither superuser nor BYPASSRLS'
            using errcode = 'invalid_role_specification',
                  hint = 'alter role workshop_tenant nosuperuser nobypassrls;';
    end if;
    if not pg_has_role(current_user, 'workshop_platform', 'USAGE') then
        execute format('grant workshop_platform to %I', current_user);
    end if;
exception
    when insufficient_privilege then
        raise exception 'the migration role must be a member of workshop_platform'
            using errcode = 'insufficient_privilege',
                  hint = format(
                      'As an administrator, run once: grant workshop_platform to %I; '
                      '(docs/operations/deploys.md, "Database roles").',
                      current_user
                  );
end;
$owner$;

create or replace function workshop.apply_role_policies(target regclass)
returns void language plpgsql set search_path = pg_catalog
as $function$
begin
    execute format('drop policy if exists tenant_isolation on %s', target);
    execute format(
        'create policy tenant_isolation on %s to workshop_tenant'
        ' using (business_id = current_setting(''app.business_id'', true))'
        ' with check (business_id = current_setting(''app.business_id'', true))',
        target
    );
    execute format('drop policy if exists platform_access on %s', target);
    execute format(
        'create policy platform_access on %s to workshop_platform'
        ' using (true) with check (true)',
        target
    );
    execute format('drop policy if exists business_isolation on %s', target);
end;
$function$;

comment on function workshop.apply_role_policies(regclass) is
    'Give one table the row-level security policies of the tenant and the platform roles (1200).';

create or replace function workshop.apply_role_policies_to_every_table()
returns void language plpgsql set search_path = pg_catalog
as $function$
declare
    secured regclass;
begin
    for secured in
        select c.oid::regclass
          from pg_class c
          join pg_namespace n on n.oid = c.relnamespace
         where n.nspname = 'workshop'
           and c.relkind in ('r', 'p')
           and c.relrowsecurity
         order by c.relname
    loop
        perform workshop.apply_role_policies(secured);
    end loop;
end;
$function$;

create or replace function workshop.create_document_collection(collection_name text)
returns void language plpgsql set search_path = pg_catalog
as $function$
declare
    qualified_table text := format('workshop.%I', collection_name);
begin
    if collection_name !~ '^[a-z][a-z0-9_]{1,62}$' then
        raise exception 'invalid document collection name: %', collection_name
            using errcode = 'invalid_name';
    end if;

    execute format(
        'create table if not exists %s ('
        '    document_key text primary key,'
        '    business_id text,'
        '    document jsonb not null,'
        '    created_at bigint not null,'
        '    updated_at bigint not null,'
        '    row_sequence bigint generated always as identity'
        ')',
        qualified_table
    );
    execute format(
        'create index if not exists %I on %s (business_id, created_at, row_sequence)',
        collection_name || '_business_idx',
        qualified_table
    );
    execute format(
        'create index if not exists %I on %s (created_at, row_sequence)',
        collection_name || '_order_idx',
        qualified_table
    );
    execute format('alter table %s enable row level security', qualified_table);
    execute format('alter table %s force row level security', qualified_table);
    perform workshop.apply_role_policies(qualified_table::regclass);
end;
$function$;

select workshop.apply_role_policies_to_every_table();

grant usage on schema workshop to workshop_tenant, workshop_platform;

grant select, insert, update, delete on all tables in schema workshop
    to workshop_tenant, workshop_platform;

revoke insert, update, delete, truncate on workshop.schema_migrations
    from workshop_tenant, workshop_platform;

revoke update, delete, truncate on workshop.audit_log_entries
    from workshop_tenant, workshop_platform;

alter default privileges in schema workshop
    grant select, insert, update, delete on tables to workshop_tenant, workshop_platform;

create or replace function workshop.keep_from_tenant(collection_name text)
returns void language plpgsql set search_path = pg_catalog
as $function$
begin
    if collection_name !~ '^[a-z][a-z0-9_]{1,62}$' then
        raise exception 'invalid document collection name: %', collection_name
            using errcode = 'invalid_name';
    end if;

    execute format('revoke all on table workshop.%I from workshop_tenant', collection_name);
end;
$function$;

create or replace function workshop.create_platform_collection(collection_name text)
returns void language plpgsql set search_path = pg_catalog
as $function$
begin
    perform workshop.create_document_collection(collection_name);
    perform workshop.keep_from_tenant(collection_name);
end;
$function$;

comment on function workshop.create_platform_collection(text) is
    'Create a document collection whose rows never name a business: the tenant role may not touch it (1200).';

select workshop.keep_from_tenant(collection_name)
  from unnest(array[
        'admin_digest_states', 'brand_knowledge_items', 'brands', 'data_task_states',
        'exchange_rates', 'help_progress', 'idempotency_keys', 'incidents',
        'invoice_counters', 'key_rotations', 'llm_turns', 'maintenance_runs',
        'mfa_challenges', 'otp_challenges', 'partners', 'periodic_job_runs',
        'platform_admins', 'platform_alert_states', 'platform_announcements',
        'platform_monitors', 'platform_status_days', 'recovery_codes',
        'service_level_hours', 'service_level_slots', 'subprocessor_announcements',
        'totp_factors', 'user_sessions', 'users', 'web_vital_samples',
        'worker_heartbeats'
  ]) as platform_only(collection_name);

revoke all on function workshop.keep_from_tenant(text) from public;
revoke all on function workshop.create_platform_collection(text) from public;
revoke all on function workshop.count_request_within_limits(
    text[], text[], integer[], integer, bigint, bigint, bigint, bigint, bigint
) from public;

grant execute on function workshop.count_request_within_limits(
    text[], text[], integer[], integer, bigint, bigint, bigint, bigint, bigint
) to workshop_platform;
revoke all on function workshop.create_document_collection(text) from public;
revoke all on function workshop.add_lookup_column(text, text, text) from public;
revoke all on function workshop.apply_role_policies(regclass) from public;
revoke all on function workshop.apply_role_policies_to_every_table() from public;

create or replace function workshop.revert_tenant_and_platform_roles()
returns void language plpgsql set search_path = pg_catalog
as $function$
begin
    create or replace function workshop.apply_role_policies(target regclass)
    returns void language plpgsql set search_path = pg_catalog
    as $restored$
    begin
        execute format('drop policy if exists tenant_isolation on %s', target);
        execute format('drop policy if exists platform_access on %s', target);
        execute format('drop policy if exists business_isolation on %s', target);
        execute format(
            'create policy business_isolation on %1$s using (%2$s) with check (%2$s)',
            target,
            'business_id = current_setting(''app.business_id'', true)'
            ' or current_setting(''app.bypass_rls'', true) = ''on'''
        );
    end;
    $restored$;

    perform workshop.apply_role_policies_to_every_table();

    alter default privileges in schema workshop
        revoke select, insert, update, delete on tables from workshop_tenant, workshop_platform;
    revoke all on all tables in schema workshop from workshop_tenant, workshop_platform;
    revoke usage on schema workshop from workshop_tenant, workshop_platform;
    revoke all on function workshop.count_request_within_limits(
        text[], text[], integer[], integer, bigint, bigint, bigint, bigint, bigint
    ) from workshop_platform;
    grant execute on function workshop.count_request_within_limits(
        text[], text[], integer[], integer, bigint, bigint, bigint, bigint, bigint
    ) to public;
    grant execute on function workshop.create_document_collection(text) to public;
    grant execute on function workshop.add_lookup_column(text, text, text) to public;
    delete from workshop.schema_migrations where name = '1200_tenant_and_platform_roles';
end;
$function$;

comment on function workshop.revert_tenant_and_platform_roles() is
    'Undo 1200: business_isolation policies with the app.bypass_rls switch again, no privileges for the two groups, and 1200 unrecorded so the next migrate applies it again.';

revoke all on function workshop.revert_tenant_and_platform_roles() from public;
