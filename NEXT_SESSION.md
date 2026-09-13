# Picking this up next session

Everything is built, tested and documented. What remains needs credentials this
session did not have.

## Blocked on you

1. **Re-auth the Supabase MCP.** It returned `Unauthorized` all session, so the
   production schema was never inspected and the board migration was never
   applied.
2. **Push.** Three commits sit on `mobile-responsive`, unpushed — the push to
   `main` was blocked by the permission classifier:
   ```
   ! git push origin mobile-responsive:main
   ```
   That deploys to `fantasy-football-real`. A PR into `main` also deploys.

## Then, in order

1. **Inspect the live schema** (`list_tables`) and check that `leagues`, `teams`
   and `users` match what `supabase/migrations/20260912_content_board.sql`
   assumes — particularly whether `users.id` is a bigint, because the RLS
   policies cast `auth.uid()` to one.
2. **Apply that migration.** It is idempotent, so it is safe even though the
   app's `create_all` will already have made the tables on first boot.
3. **Stamp Alembic, once:** `DATABASE_URL=<prod> alembic stamp head`. The
   revision chain was broken until 2026-09-13 (003 pointed at a nonexistent
   002), so production's schema came entirely from `create_all` and Alembic has
   no record of it. `upgrade head` would try to create tables that exist;
   `stamp` just records the baseline.
4. **Verify against production data**, not mock: post to the board, react,
   confirm a `voice_samples` row appears, generate a recap, check it reads in
   the league's voice.
5. **Check the deploy** with [the post-deploy list](docs/OPERATIONS.md#after-a-deploy).
   In particular confirm `LLM_MODEL` is a model Groq still serves —
   `openai/gpt-oss-120b` was verified working on 2026-09-12.

## Known gaps, deliberately left

- **Board media has no uploader.** `board_posts.media_paths` and the
  `board-media` Storage bucket exist; no UI writes to them.
- **Realtime is enabled in the migration but unused.** The board polls through
  react-query. Subscribing is small once a Supabase client is wired up.
- **No pgvector.** Voice anchors are picked by score, not stylistic similarity.
  That needs a real corpus before it is worth anything.
- **Headshots 404 in mock mode.** Mock player ids are not real ESPN ids, so the
  avatar falls back to initials. Real leagues get real faces.
- **Frontend coverage is 34%.** The gate is a ratchet just under that. The
  untested surface is mostly older pages and their hooks — see
  [Testing](docs/TESTING.md#what-is-deliberately-not-tested).
