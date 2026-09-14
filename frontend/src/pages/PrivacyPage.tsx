import React from 'react';
import { LegalPage } from '@/components/layout/PublicLayout';

export const PrivacyPage: React.FC = () => (
  <LegalPage title="Privacy Policy" updated="September 14, 2026">
    <p>
      Fantasy Football Assistant is a personal project that helps you manage fantasy
      football leagues you already have on ESPN and Sleeper. This policy describes
      exactly what it stores, why, and who else sees it. It is written to be read
      rather than skimmed, so it is short.
    </p>

    <section>
      <h2>What is collected</h2>
      <p><strong>When you create an account:</strong></p>
      <ul>
        <li>Your email address, which identifies the account.</li>
        <li>Your name, if you choose to provide one.</li>
        <li>A cryptographic hash of your password. The password itself is never stored.</li>
      </ul>
      <p><strong>If you sign in with Google,</strong> Google sends your Google account
        identifier, email address, name and profile picture URL. Nothing else is
        requested, and no Google service beyond sign-in is accessed.</p>
      <p><strong>If you connect a private ESPN league,</strong> the ESPN cookies you
        provide are encrypted before they are stored, and are used only to read that
        league on your behalf.</p>
      <p><strong>From the platforms you connect,</strong> league, team, roster, matchup
        and player data is fetched from ESPN and Sleeper so the app can show and analyse
        it.</p>
    </section>

    <section>
      <h2>What is not collected</h2>
      <ul>
        <li>No analytics, no tracking pixels, no advertising identifiers. There are no
          third-party trackers in this app at all.</li>
        <li>No tracking cookies. Your session is held in your own browser's local
          storage and is sent only to this app's own API.</li>
        <li>No payment details, because nothing here is paid for.</li>
      </ul>
    </section>

    <section>
      <h2>Who else processes it</h2>
      <ul>
        <li><strong>Supabase</strong> hosts the database where your account and league
          data are stored.</li>
        <li><strong>Vercel</strong> hosts the application and its API.</li>
        <li><strong>Groq</strong> runs the language model behind recaps and
          recommendations. Roster and matchup context is sent there to generate that
          text. Your email address, password hash and ESPN cookies are never sent.</li>
        <li><strong>ESPN and Sleeper</strong> receive requests for the league data you
          asked the app to read.</li>
        <li><strong>Google</strong> receives a sign-in request when you use the Google
          button.</li>
      </ul>
      <p>Your data is not sold, rented, or shared with anyone else.</p>
    </section>

    <section>
      <h2>Google user data</h2>
      <p>
        This app's use of information received from Google APIs follows the{' '}
        <a
          href="https://developers.google.com/terms/api-services-user-data-policy"
          target="_blank"
          rel="noreferrer noopener"
        >
          Google API Services User Data Policy
        </a>
        , including its Limited Use requirements. Google sign-in data is used only to
        create and identify your account. It is never used for advertising, never sold,
        and never shared beyond the processors listed above.
      </p>
    </section>

    <section>
      <h2>Keeping and deleting it</h2>
      <p>
        Your data is kept while your account exists. To delete your account and
        everything attached to it, email{' '}
        <a href="mailto:davidjmorgan26@gmail.com">davidjmorgan26@gmail.com</a> and it
        will be removed. You can also disconnect this app from your Google account at
        any time at{' '}
        <a href="https://myaccount.google.com/permissions" target="_blank" rel="noreferrer noopener">
          your Google account permissions page
        </a>
        , and you can clear stored ESPN cookies yourself from the profile page.
      </p>
    </section>

    <section>
      <h2>Children</h2>
      <p>This app is not directed at children under 13 and accounts should not be
        created for them.</p>
    </section>

    <section>
      <h2>Changes and contact</h2>
      <p>
        If this policy changes, the date at the top changes with it. Questions go to{' '}
        <a href="mailto:davidjmorgan26@gmail.com">davidjmorgan26@gmail.com</a>.
      </p>
    </section>
  </LegalPage>
);
