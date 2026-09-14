-- Google sign-in schema change.
-- Mirrors backend/alembic/versions/0002_google_auth.py.
--
-- MUST be applied BEFORE deploying the code that uses it: the User model
-- selects google_sub on every query, so the new code against the old schema
-- returns 500 on every authenticated request.
--
-- Safe to run on a live database. Every statement is additive or a constraint
-- relaxation; nothing is dropped and no row is rewritten.

alter table public.users add column if not exists google_sub varchar(255);
alter table public.users add column if not exists avatar_url text;

-- Unique so one Google account cannot be attached to two of ours; nullable so
-- every existing password account stays valid.
create unique index if not exists ix_users_google_sub on public.users (google_sub);

-- A Google-only account has no password to store.
alter table public.users alter column hashed_password drop not null;

-- The application normalizes addresses, but the plain unique index on `email`
-- would still accept "Dave@x.com" alongside "dave@x.com", and those two rows
-- would then fight over one Google account.
create unique index if not exists ix_users_email_lower on public.users (lower(email));

-- Record the migration so `alembic current` matches reality.
update public.alembic_version set version_num = '0002';
