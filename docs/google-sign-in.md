# Google Sign-In

## How it works

We use **Google Identity Services** with the ID-token flow, not a redirect
/ authorization-code flow.

The browser renders Google's button, the user picks an account, and Google
hands the page a signed JWT. The page POSTs it to `/api/auth/google`, the
backend verifies it against Google's published keys, and returns one of our
normal bearer tokens. That is the whole flow.

This means:

- **There is no client secret.** Nothing about this setup needs to be kept
  confidential on our side, which matters on a serverless backend with no
  durable session store.
- **There is no callback route** and no redirect URI to keep in sync across
  preview deployments.
- The client id is public and is served from `/api/meta`, so rotating it is an
  env var change rather than a frontend rebuild.

Verification lives in `backend/app/services/google_oauth.py`. Four checks have
to pass: signature against the JWKS, `aud` equal to our client id, `iss` is
Google, and `exp`/`iat` within a small clock-skew allowance. The audience check
is the one people skip: Google signs every app's tokens with the same keys, so
without it a token minted for any other Google site would be accepted here.

## Account linking

`AuthService.login_with_google` resolves an account in this order:

1. **Known `google_sub`.** Sign that user in.
2. **No `google_sub`, but the email matches an existing account.** Link them.
   This is what attaches a pre-existing password account to Google the first
   time its owner presses the button, instead of stranding their leagues on a
   second account.
3. **Neither.** Create a passwordless account.

Cases 2 and 3 both require `email_verified` on the token. That check is the
security of the whole endpoint: a Workspace domain can issue tokens carrying
unverified addresses, so without it someone could claim an account by asserting
its email.

Notes on the edges:

- We key on `sub`, Google's immutable subject id, not email. A user who changes
  their Google address stays the same account here.
- Emails are normalized to lowercase everywhere, and a unique index on
  `lower(email)` enforces it in the database. Without this, an account
  registered as `Dave@x.com` would not match Google's `dave@x.com` and the user
  would silently get a second, empty account.
- `users.hashed_password` is nullable. Every code path that verifies a password
  checks for `None` first, because passlib raises on a null hash rather than
  returning False.
- A Google-only user can set a first password from the profile page without
  providing a current one. That is their only recovery path if they ever lose
  access to the Google account.

## Google Cloud configuration

All of this is already done. Recorded here because none of it lives in the
repository, so this file is the only record of how production is wired.

| Thing | Value |
| --- | --- |
| Project | `fantasy-football-asst` (number 446031807254) |
| Organization | none, it is a personal account |
| Client type | Web application, "Fantasy Football Assistant Web" |
| Client id | `446031807254-lakhqujd7p746v7rpgcfg9elaaruhcjm.apps.googleusercontent.com` |
| Publishing status | Testing |

Authorized JavaScript origins:

- `https://fantasy-football-real.vercel.app`
- `http://localhost:3000`
- `http://localhost:5173`

Authorized redirect URIs: **none**. This flow does not redirect. Origins must
match exactly, scheme and port included; a mismatch shows up as the button
silently failing to render, with `origin_mismatch` in the browser console.

The client id is set as `GOOGLE_CLIENT_ID` on the `fantasy-football-real`
Vercel project and in `backend/.env` for local work. It is served to the
frontend from `/api/meta`, so rotating it needs a redeploy but not a rebuild.

Creating the OAuth client is Console-only. Google has never exposed it through
`gcloud` or a public API: the `iap oauth-brands` endpoint rejects it with
`"Project must belong to an organization."` and, even with an org, only issues
IAP-internal clients rather than a general web client.

### Testing mode limits who can sign in

The app is in **Testing**, so only accounts on the test-user list can sign in.
Everyone else gets `access_denied`. Currently listed:

- `davidjmorgan26@gmail.com`

Add more at [Audience](https://console.cloud.google.com/auth/audience?project=fantasy-football-asst),
up to 100 over the app's lifetime.

Everything the Branding page asks for now exists and is public, served by the
app itself so it stays on the authorized domain:

| Field | Value |
| --- | --- |
| Application home page | `https://fantasy-football-real.vercel.app/` |
| Privacy policy link | `https://fantasy-football-real.vercel.app/privacy` |
| Terms of service link | `https://fantasy-football-real.vercel.app/terms` |
| App logo | `docs/assets/google-consent-logo.png` |

`/` serves the dashboard to signed-in users and a landing page to everyone
else, because Google wants a home page reachable without an account. See
`HomeRoute` in `frontend/src/App.tsx`.

A 120x120 logo for the Branding page is committed at
`docs/assets/google-consent-logo.png` (23KB, well under Google's 1MB cap). It
is flattened onto the tile's own dark background rather than left transparent,
because the consent card renders it on white.

To let anyone sign in, publish the app. The Console requires the
[Branding](https://console.cloud.google.com/auth/branding?project=fantasy-football-asst)
page to be completed first (app logo, home page, privacy policy and terms
URLs). Publishing itself needs no Google verification review, because the only
scopes requested are `openid`, `email` and `profile`, all non-sensitive.

## Deploy order

The schema change must land **before** the code. The `User` model selects
`google_sub` on every query, so new code against the old schema returns 500 on
every authenticated request.

Apply `docs/google-sign-in-migration.sql` (or
`alembic upgrade head` with production `DATABASE_URL`) first, then deploy.
