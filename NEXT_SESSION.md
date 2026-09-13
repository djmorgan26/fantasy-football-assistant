# Picking this up next session

Everything below is built, tested and verified locally. What is left needs
credentials this session did not have.

## What you need to do first

1. **Re-auth the Supabase MCP.** It returned `Unauthorized` all session, so the
   production schema was never inspected or migrated.
2. **Push the mobile work.** Branch `mobile-responsive` is committed but the
   push to `main` was blocked by the permission classifier:
   ```
   ! git push origin mobile-responsive:main
   ```

## Then, in order

1. **Inspect the live schema** (`list_tables`) and confirm `leagues`, `teams`
   and `users` match what `supabase/migrations/20260912_content_board.sql`
   references — particularly whether `users.id` is a bigint, because the RLS
   policies cast `auth.uid()` to one.
2. **Apply the migration.** It is idempotent, so it is safe to run even though
   the app's `create_all` may already have made the tables on first boot.
3. **Verify end to end against production data**, not mock: post to the board,
   react, confirm a `voice_samples` row appears, then generate a recap and
   check it reads in the league's voice.
4. **Deploy.** `git push origin <branch>:main` ships to `fantasy-football-real`.
   A PR into main deploys too.

## Production environment variables to check

- `LLM_MODEL` — must be a live Groq model. `openai/gpt-oss-120b` was verified
  working this session. List them with
  `GET https://api.groq.com/openai/v1/models` before trusting any pin.
- Stale pins are worse than missing ones: prefer removing a pin so the code
  default wins.

## Known gaps, deliberately left

- **Board media is wired but has no uploader.** `board_posts.media_paths` and
  the `board-media` Storage bucket exist; no UI writes to them yet.
- **Realtime is enabled in the migration but the client does not subscribe.**
  The board polls via react-query. Subscribing is a small change once the
  Supabase client is wired up.
- **No pgvector.** Voice anchors are picked by score, not by stylistic
  similarity. That was the phase-4 idea in the teardown and it needs a real
  corpus before it is worth anything.
- **Headshots 404 in mock mode.** Mock player ids are not real ESPN ids, so the
  avatar falls back to initials. Real leagues get real faces.
