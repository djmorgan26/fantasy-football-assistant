import React from 'react';
import { Link } from 'react-router-dom';
import { PublicLayout } from '@/components/layout/PublicLayout';
import { BrandMark } from '@/components/ui/BrandMark';

// Only things the app actually does. A landing page that promises features
// that are not there is the fastest way to make the rest of it untrustworthy.
const FEATURES: { title: string; body: string }[] = [
  {
    title: 'Both platforms, one place',
    body: 'Connect ESPN and Sleeper leagues side by side and see every roster you own without switching apps.',
  },
  {
    title: 'A game plan, not a data dump',
    body: 'Spots an injured starter, finds the bench player who should replace him, and weighs waiver adds and trades against the drop in points.',
  },
  {
    title: 'Game day scoreboard',
    body: 'Live matchup scoring for every league you are in, with the players still to play.',
  },
  {
    title: 'Draft room',
    body: 'Live draft board with projections and positional runs while you pick.',
  },
  {
    title: 'Press box',
    body: 'Weekly recaps and league awards written from what actually happened in your matchups.',
  },
  {
    title: 'Injury and news watch',
    body: 'Player news filtered down to the people on your rosters, not the whole league.',
  },
];

export const LandingPage: React.FC = () => (
  <PublicLayout>
    <section className="mx-auto w-full max-w-5xl px-4 py-16 sm:px-6 sm:py-24">
      <div className="flex flex-col items-center text-center">
        <BrandMark className="h-20 w-20" />
        <h1 className="mt-6 max-w-2xl font-display text-4xl font-extrabold tracking-tight text-fg sm:text-5xl">
          Your fantasy football leagues, actually thought about
        </h1>
        <p className="mt-5 max-w-xl text-lg leading-relaxed text-fg-muted">
          Connect your ESPN and Sleeper leagues and get lineup calls, waiver targets
          and trade angles that account for who is hurt, who is hot, and what it costs
          you to fix it.
        </p>
        <div className="mt-9 flex flex-wrap items-center justify-center gap-3">
          <Link
            to="/register"
            className="rounded-pill bg-brand px-6 py-3 text-base font-semibold text-brand-fg shadow-elevation-2 transition-shadow hover:shadow-elevation-3 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          >
            Create an account
          </Link>
          <Link
            to="/login"
            className="rounded-pill border border-border px-6 py-3 text-base font-semibold text-fg transition-colors hover:border-border-strong hover:bg-surface-sunken focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            Sign in
          </Link>
        </div>
        <p className="mt-4 text-sm text-fg-subtle">
          Free. No card, and no ESPN password: public leagues need nothing at all.
        </p>
      </div>

      <ul className="mt-20 grid gap-x-8 gap-y-10 sm:grid-cols-2 lg:grid-cols-3">
        {FEATURES.map((feature) => (
          <li key={feature.title}>
            <h2 className="font-display text-lg font-bold text-fg">{feature.title}</h2>
            <p className="mt-2 text-[15px] leading-relaxed text-fg-muted">{feature.body}</p>
          </li>
        ))}
      </ul>

      <p className="mt-20 text-center text-sm text-fg-subtle">
        An independent project. Not affiliated with ESPN, Sleeper or the NFL.
      </p>
    </section>
  </PublicLayout>
);
