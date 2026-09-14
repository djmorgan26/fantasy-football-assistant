-- ============================================================================
-- league_members: more than one manager per league
--
-- Run this against the Supabase project BEFORE deploying the matching backend.
-- Idempotent, so re-running it is harmless.
--
-- Why it exists: a platform league is one row in `leagues`, and until now the
-- only user attached to it was `owner_user_id`. Both connect endpoints
-- reassigned that column to whoever had connected most recently, so the second
-- manager to link the same ESPN or Sleeper league took it from the first, who
-- then got "League not found or access denied" on every page, the board
-- included. This table is the fix, and it is also what the board needs to work
-- as designed: the managers of one league resolve to one league row and post
-- to one board.
-- ============================================================================

create table if not exists public.league_members (
    id              serial primary key,
    league_id       integer      not null references public.leagues(id) on delete cascade,
    user_id         integer      not null references public.users(id) on delete cascade,
    -- "owner" is whoever connected it first. Nothing branches on this yet.
    role            varchar(32)  not null default 'member',
    -- This manager's own Sleeper account. leagues.sleeper_user_id is the
    -- owner's, and is the wrong roster to answer anyone else's draft questions
    -- with.
    sleeper_user_id varchar(255),
    -- The team this manager runs. It lives here rather than on
    -- teams.owner_user_id because that column holds one user, so two people who
    -- co-own a team fought over it: the second to claim silently unclaimed the
    -- first, and their roster disappeared from the app.
    team_id         integer      references public.teams(id) on delete set null,
    created_at      timestamptz  not null default now(),
    constraint uq_league_members_league_user unique (league_id, user_id)
);

create index if not exists ix_league_members_id        on public.league_members (id);
create index if not exists ix_league_members_league_id on public.league_members (league_id);
create index if not exists ix_league_members_user_id   on public.league_members (user_id);

-- Every current owner is a member, so the new access rule (owner OR member) is
-- a superset of the old one from the first request after deploy.
insert into public.league_members (league_id, user_id, role, sleeper_user_id)
select id, owner_user_id, 'owner', sleeper_user_id
from public.leagues
where owner_user_id is not null
on conflict (league_id, user_id) do nothing;

-- Anyone holding a team in a league belongs to it, owner or not, and their
-- existing claim becomes their membership's claim.
insert into public.league_members (league_id, user_id, role, team_id)
select league_id, owner_user_id, 'member', id
from public.teams
where owner_user_id is not null
on conflict (league_id, user_id) do update set team_id = excluded.team_id;

alter table public.league_members enable row level security;

drop policy if exists league_members_self_read on public.league_members;
create policy league_members_self_read on public.league_members
    for select using (user_id = auth.uid()::text::integer);

-- Teach the board's RLS the same rule the API now uses. (As documented in the
-- content-board migration, these policies gate nothing yet: the app holds its
-- own JWT, not a Supabase Auth one, so auth.uid() is NULL and everything but
-- service_role denies. This keeps the two definitions from drifting apart
-- before that changes.)
create or replace function public.is_league_member(target_league_id integer)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
    select exists (
        select 1 from public.leagues l
        where l.id = target_league_id
          and l.owner_user_id = auth.uid()::text::integer
    )
    or exists (
        select 1 from public.league_members m
        where m.league_id = target_league_id
          and m.user_id = auth.uid()::text::integer
    )
    or exists (
        select 1 from public.teams t
        where t.league_id = target_league_id
          and t.owner_user_id = auth.uid()::text::integer
    )
$$;

revoke execute on function public.is_league_member(integer) from public;
revoke execute on function public.is_league_member(integer) from anon;
grant  execute on function public.is_league_member(integer) to authenticated;
grant  execute on function public.is_league_member(integer) to service_role;

update public.alembic_version set version_num = '0003';
