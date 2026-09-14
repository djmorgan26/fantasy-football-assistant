import React from 'react';
import { LegalPage } from '@/components/layout/PublicLayout';

export const TermsPage: React.FC = () => (
  <LegalPage title="Terms of Service" updated="September 14, 2026">
    <p>
      Fantasy Football Assistant is a free personal project. Using it means accepting
      these terms. If you do not accept them, please do not use it.
    </p>

    <section>
      <h2>What this is</h2>
      <p>
        A tool that reads fantasy football leagues you already have on ESPN and
        Sleeper, and helps you analyse them: lineup and waiver suggestions, trade
        analysis, draft tools, weekly recaps, and league news.
      </p>
    </section>

    <section>
      <h2>Your account</h2>
      <ul>
        <li>Keep your password and your ESPN cookies to yourself. Anyone holding them
          can reach your leagues.</li>
        <li>Connect only leagues you are actually a member of.</li>
        <li>Tell us at <a href="mailto:davidjmorgan26@gmail.com">davidjmorgan26@gmail.com</a>{' '}
          if you think your account has been accessed by someone else.</li>
      </ul>
    </section>

    <section>
      <h2>Advice is a suggestion, not a guarantee</h2>
      <p>
        Recommendations, projections and recaps are generated automatically, partly by
        a language model, from data that is frequently incomplete or out of date.
        They can be wrong, and sometimes confidently so. Every roster decision is
        yours. Nothing here is betting advice, and nothing here should be treated as a
        prediction of what will actually happen.
      </p>
    </section>

    <section>
      <h2>Acceptable use</h2>
      <p>Do not use this app to break into accounts that are not yours, to scrape or
        resell data at scale, to disrupt the service, or to break ESPN's or Sleeper's
        own terms.</p>
    </section>

    <section>
      <h2>Not affiliated with ESPN, Sleeper or the NFL</h2>
      <p>
        This is an independent project. It is not endorsed by, affiliated with, or
        sponsored by ESPN, Sleeper, the National Football League, or any of its teams.
        Those names and marks belong to their owners and are used only to say which
        service a league comes from. Those services can change or withdraw access at
        any time, which may stop parts of this app from working.
      </p>
    </section>

    <section>
      <h2>No warranty, and limits</h2>
      <p>
        The app is provided as is, with no warranty of any kind. It may be unavailable,
        lose data, or be discontinued without notice. To the extent the law allows,
        the author is not liable for any loss arising from your use of it. It is free,
        and it is offered on that basis.
      </p>
    </section>

    <section>
      <h2>Ending it</h2>
      <p>
        You can stop using the app whenever you like and ask for your account to be
        deleted by email. Accounts that abuse the service may be suspended.
      </p>
    </section>

    <section>
      <h2>Changes and contact</h2>
      <p>
        If these terms change, the date at the top changes with them. Questions go to{' '}
        <a href="mailto:davidjmorgan26@gmail.com">davidjmorgan26@gmail.com</a>.
      </p>
    </section>
  </LegalPage>
);
