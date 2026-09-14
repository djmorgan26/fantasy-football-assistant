-- ============================================================================
-- Content board + voice corpus
--
-- Run this against the Supabase project once (SQL editor, or `supabase db push`).
-- It is idempotent: every statement is IF NOT EXISTS / OR REPLACE, so re-running
-- it after the app's own create_all has already made the tables is harmless.
--
-- The app reaches Postgres through the Supavisor transaction pooler as the
-- service role, so API-level league checks are what actually gate access today.
-- The policies at the bottom exist so that a direct PostgREST/Realtime client
-- (the live-commenting path) is gated too, rather than trusting the client.
-- ============================================================================

-- ---------------------------------------------------------------- posts ----
create table if not exists public.board_posts (
    id              serial primary key,
    league_id       integer      not null references public.leagues(id) on delete cascade,
    -- NULL author means the AI wrote it. Those posts are rated like any other;
    -- that rating is the only training signal the voice profile ever gets.
    author_user_id  integer      references public.users(id) on delete set null,
    kind            varchar(32) not null default 'post',
    title           varchar(300),
    body            text        not null,
    media_paths     jsonb       not null default '[]'::jsonb,
    week            integer,
    generated_by    varchar(120),
    allow_training  boolean     not null default true,
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now()
);

create index if not exists ix_board_posts_league_created
    on public.board_posts (league_id, created_at desc);
create index if not exists ix_board_posts_author
    on public.board_posts (author_user_id);

-- ------------------------------------------------------------- comments ----
create table if not exists public.board_comments (
    id              serial primary key,
    post_id         integer      not null references public.board_posts(id) on delete cascade,
    parent_id       integer      references public.board_comments(id) on delete cascade,
    author_user_id  integer      not null references public.users(id) on delete cascade,
    body            text        not null,
    created_at      timestamptz not null default now()
);

create index if not exists ix_board_comments_post
    on public.board_comments (post_id, created_at);

-- ------------------------------------------------------------ reactions ----
-- Stored as varchar rather than a native enum: adding a sixth reaction should
-- be a code change, not a migration, and SQLite gets identical DDL locally.
create table if not exists public.board_reactions (
    id          serial primary key,
    post_id     integer      references public.board_posts(id) on delete cascade,
    comment_id  integer      references public.board_comments(id) on delete cascade,
    user_id     integer      not null references public.users(id) on delete cascade,
    reaction    varchar(16) not null,
    created_at  timestamptz not null default now(),

    constraint ck_board_reactions_one_target
        check (num_nonnulls(post_id, comment_id) = 1),
    constraint ck_board_reactions_kind
        check (reaction in ('savage', 'funny', 'brutal', 'smart', 'cold')),
    -- Tapping the same reaction twice is a toggle, not a second vote.
    constraint uq_board_reaction_post    unique (user_id, post_id, reaction),
    constraint uq_board_reaction_comment unique (user_id, comment_id, reaction)
);

create index if not exists ix_board_reactions_post    on public.board_reactions (post_id);
create index if not exists ix_board_reactions_comment on public.board_reactions (comment_id);

-- --------------------------------------------------------- voice corpus ----
-- What the content generator reads as few-shot style anchors, harvested from
-- the posts this league rated highest. Replaces the hand-typed humor_examples
-- on league_content_profiles, which nobody ever filled in.
create table if not exists public.voice_samples (
    id              serial primary key,
    league_id       integer      not null references public.leagues(id) on delete cascade,
    source_post_id  integer      references public.board_posts(id) on delete set null,
    author_user_id  integer      references public.users(id) on delete set null,
    title           varchar(300),
    text            text        not null,
    score           integer     not null default 0,
    tags            jsonb       not null default '[]'::jsonb,
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now()
);

create index if not exists ix_voice_samples_league_score
    on public.voice_samples (league_id, score desc);

-- -------------------------------------------------------------- scoring ----
-- Weighted reactions plus comment volume. A reply is the strongest evidence a
-- post landed, so it counts double; a cold take is the only thing that
-- subtracts, and it is what keeps a flat recap out of the corpus.
create or replace view public.board_post_scores
with (security_invoker = on) as
select
    p.id,
    p.league_id,
    coalesce(sum(
        case r.reaction
            when 'savage' then 3
            when 'funny'  then 3
            when 'brutal' then 2
            when 'smart'  then 2
            when 'cold'   then -2
            else 0
        end
    ), 0)
    + 2 * (select count(*) from public.board_comments c where c.post_id = p.id) as score
from public.board_posts p
left join public.board_reactions r on r.post_id = p.id
group by p.id, p.league_id;

-- ------------------------------------------------------------------ RLS ----
-- The board is private to a league. Membership is "you own a team in it, or you
-- connected it", which is how the rest of the app decides access.
alter table public.board_posts     enable row level security;
alter table public.board_comments  enable row level security;
alter table public.board_reactions enable row level security;
alter table public.voice_samples   enable row level security;

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
        select 1 from public.teams t
        where t.league_id = target_league_id
          and t.owner_user_id = auth.uid()::text::integer
    );
$$;

drop policy if exists board_posts_member_read on public.board_posts;
create policy board_posts_member_read on public.board_posts
    for select using (public.is_league_member(league_id));

drop policy if exists board_posts_member_write on public.board_posts;
create policy board_posts_member_write on public.board_posts
    for insert with check (public.is_league_member(league_id));

drop policy if exists board_posts_author_update on public.board_posts;
create policy board_posts_author_update on public.board_posts
    for update using (
        public.is_league_member(league_id)
        and (author_user_id = auth.uid()::text::integer or author_user_id is null)
    );

drop policy if exists board_posts_author_delete on public.board_posts;
create policy board_posts_author_delete on public.board_posts
    for delete using (
        public.is_league_member(league_id)
        and (author_user_id = auth.uid()::text::integer or author_user_id is null)
    );

drop policy if exists board_comments_member_read on public.board_comments;
create policy board_comments_member_read on public.board_comments
    for select using (exists (
        select 1 from public.board_posts p
        where p.id = post_id and public.is_league_member(p.league_id)
    ));

drop policy if exists board_comments_member_write on public.board_comments;
create policy board_comments_member_write on public.board_comments
    for insert with check (
        author_user_id = auth.uid()::text::integer
        and exists (
            select 1 from public.board_posts p
            where p.id = post_id and public.is_league_member(p.league_id)
        )
    );

drop policy if exists board_comments_author_delete on public.board_comments;
create policy board_comments_author_delete on public.board_comments
    for delete using (author_user_id = auth.uid()::text::integer);

drop policy if exists board_reactions_member_read on public.board_reactions;
create policy board_reactions_member_read on public.board_reactions
    for select using (exists (
        select 1 from public.board_posts p
        where p.id = post_id and public.is_league_member(p.league_id)
    ));

drop policy if exists board_reactions_own_write on public.board_reactions;
create policy board_reactions_own_write on public.board_reactions
    for insert with check (user_id = auth.uid()::text::integer);

drop policy if exists board_reactions_own_delete on public.board_reactions;
create policy board_reactions_own_delete on public.board_reactions
    for delete using (user_id = auth.uid()::text::integer);

-- The corpus is derived data: readable by the league, written only by the API.
drop policy if exists voice_samples_member_read on public.voice_samples;
create policy voice_samples_member_read on public.voice_samples
    for select using (public.is_league_member(league_id));

-- --------------------------------------------------------- realtime ---------
-- Live commenting with no polling and no websocket server of our own.
do $$
begin
    if exists (select 1 from pg_publication where pubname = 'supabase_realtime') then
        alter publication supabase_realtime add table public.board_posts;
        alter publication supabase_realtime add table public.board_comments;
        alter publication supabase_realtime add table public.board_reactions;
    end if;
exception
    when duplicate_object then null;   -- already published; nothing to do
end $$;

-- ---------------------------------------------------------- storage ---------
-- Images attached to posts. board_posts.media_paths holds keys into this bucket,
-- never bytes.
insert into storage.buckets (id, name, public)
values ('board-media', 'board-media', true)
on conflict (id) do nothing;

-- ------------------------------------------------------- function grants ----
-- Postgres grants EXECUTE to PUBLIC on every new function, so `anon` picks it
-- up by inheritance and revoking from `anon` alone is a no-op. Drop the PUBLIC
-- grant and hand it back only to the roles that need it. `authenticated` must
-- keep it: the policies above call this as the querying user, and without
-- EXECUTE every board SELECT fails with "permission denied".
revoke execute on function public.is_league_member(integer) from public;
revoke execute on function public.is_league_member(integer) from anon;
grant  execute on function public.is_league_member(integer) to authenticated;
grant  execute on function public.is_league_member(integer) to service_role;
