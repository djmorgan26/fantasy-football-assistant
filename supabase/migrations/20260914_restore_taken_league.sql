-- ============================================================================
-- One-off repair for the league that was taken over before league_members
-- existed. Run AFTER 20260914_league_members.sql.
--
-- What happened: user 1 (davidjmorgan26@gmail.com) connected ESPN league
-- 1725275280 "AEPI 2022" and it became league row 1. User 2
-- (jakebeinart1@gmail.com) signed up hours later and connected the same ESPN
-- league, which moved `leagues.owner_user_id` to 2 and, when he claimed team 9
-- "Bein N Co." (which the two of them co-own), moved `teams.owner_user_id` too.
-- User 1 then got "League not found or access denied" on the whole league and
-- his roster vanished.
--
-- The code no longer does either of those things. This puts the row back and
-- leaves both managers inside it.
-- ============================================================================

-- Ownership goes back to whoever connected it first.
update public.leagues
set owner_user_id = 1
where id = 1 and owner_user_id = 2;

-- Both managers are in the league, and both run team 9.
insert into public.league_members (league_id, user_id, role, team_id)
values (1, 1, 'owner',  (select id from public.teams where league_id = 1 and espn_team_id = 9)),
       (1, 2, 'member', (select id from public.teams where league_id = 1 and espn_team_id = 9))
on conflict (league_id, user_id) do update
    set role    = excluded.role,
        team_id = coalesce(public.league_members.team_id, excluded.team_id);
