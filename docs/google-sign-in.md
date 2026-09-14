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

## One-time setup

Creating the OAuth client is **Console-only**. Google has never exposed it
through `gcloud` or a public API; the `iap oauth-brands` endpoints are
IAP-specific and reject projects that do not belong to an organization.

A project has already been created: **`fantasy-football-asst`**.

1. Open the [Google Auth Platform](https://console.cloud.google.com/auth/overview)
   and select the `fantasy-football-asst` project.
2. Configure the consent screen: **External** user type, app name
   "Fantasy Football Assistant", your email for both support and developer
   contact. No scopes beyond the default `openid`, `email`, `profile` are
   needed, so the app stays out of verification review.
3. **Credentials → Create Credentials → OAuth client ID**, type
   **Web application**.
4. Under **Authorized JavaScript origins**, add:
   - `https://fantasy-football-real.vercel.app`
   - `http://localhost:3000`
   - `http://localhost:5173`

   Leave **Authorized redirect URIs** empty. This flow does not redirect.
5. Copy the client id (it ends in `.apps.googleusercontent.com`) and set it:

   ```
   vercel env add GOOGLE_CLIENT_ID production
   echo "GOOGLE_CLIENT_ID=..." >> backend/.env   # for local dev
   ```

Origins must match exactly, scheme and port included. A mismatch shows up as
the button silently failing to render, with a `origin_mismatch` error in the
browser console.

## Deploy order

The schema change must land **before** the code. The `User` model selects
`google_sub` on every query, so new code against the old schema returns 500 on
every authenticated request.

Apply `docs/google-sign-in-migration.sql` (or
`alembic upgrade head` with production `DATABASE_URL`) first, then deploy.
