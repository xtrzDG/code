#!/bin/sh
# First start of the local Postgres container (docker-compose.yml): create
# the migration role and its database, the two group roles of migration
# 1200 and the application's login roles in them, as an administrator does
# in production (docs/operations/deploys.md, "Database roles"). No role is
# a superuser or BYPASSRLS, so the row-level security of the migrations
# binds them all: the migration role owns the database and joins
# workshop_platform; the tenant pool's role sees one business at a time.
set -eu

psql --variable=ON_ERROR_STOP=1 \
  --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  --set=app_role="${WORKSHOP_DB_USER:-workshop}" \
  --set=tenant_role="${WORKSHOP_DB_USER:-workshop}_tenant_app" \
  --set=platform_role="${WORKSHOP_DB_USER:-workshop}_platform_app" \
  --set=app_password="${WORKSHOP_DB_PASSWORD:-workshop}" \
  --set=app_database="${WORKSHOP_DB_NAME:-workshop}" <<'SQL'
create role :"app_role" login password :'app_password'
  nosuperuser nobypassrls nocreatedb nocreaterole;
create database :"app_database" owner :"app_role";
create role workshop_tenant nologin nosuperuser nobypassrls;
create role workshop_platform nologin nosuperuser nobypassrls;
grant workshop_platform to :"app_role";
create role :"tenant_role" login password :'app_password'
  nosuperuser nobypassrls nocreatedb nocreaterole in role workshop_tenant;
create role :"platform_role" login password :'app_password'
  nosuperuser nobypassrls nocreatedb nocreaterole in role workshop_platform;
SQL
