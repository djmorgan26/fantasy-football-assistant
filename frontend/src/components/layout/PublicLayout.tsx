import React from 'react';
import { Link } from 'react-router-dom';
import { BrandMark } from '@/components/ui/BrandMark';

/**
 * Chrome for the pages a signed-out visitor can reach.
 *
 * Separate from Layout because that one is the signed-in application shell:
 * sidebar, league nav, the assistant dock. None of it means anything to
 * someone who has not signed in, and Google needs the home page, privacy
 * policy and terms reachable without an account.
 */
export const PublicLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div className="flex min-h-screen flex-col bg-surface">
    <header className="border-b border-border">
      <div className="mx-auto flex h-16 w-full max-w-5xl items-center justify-between gap-4 px-4 sm:px-6">
        <Link to="/" className="flex items-center gap-2.5" aria-label="Fantasy Football Assistant home">
          <BrandMark className="h-9 w-9" />
          <span className="font-display text-base font-bold text-fg sm:text-lg">
            Fantasy&nbsp;Football&nbsp;Assistant
          </span>
        </Link>
        <Link
          to="/login"
          className="rounded-pill bg-brand px-4 py-2 text-sm font-semibold text-brand-fg transition-shadow hover:shadow-elevation-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          Sign in
        </Link>
      </div>
    </header>

    <main className="flex-1">{children}</main>

    <footer className="border-t border-border">
      <div className="mx-auto flex w-full max-w-5xl flex-wrap items-center justify-between gap-x-6 gap-y-2 px-4 py-6 text-sm text-fg-muted sm:px-6">
        <span>© {new Date().getFullYear()} Fantasy Football Assistant</span>
        <nav className="flex flex-wrap items-center gap-x-5 gap-y-2">
          <Link to="/privacy" className="hover:text-fg hover:underline">Privacy</Link>
          <Link to="/terms" className="hover:text-fg hover:underline">Terms</Link>
          <a href="mailto:davidjmorgan26@gmail.com" className="hover:text-fg hover:underline">Contact</a>
        </nav>
      </div>
    </footer>
  </div>
);

/** Shared prose styling for the policy pages. */
export const LegalPage: React.FC<{
  title: string;
  updated: string;
  children: React.ReactNode;
}> = ({ title, updated, children }) => (
  <PublicLayout>
    <article className="mx-auto w-full max-w-3xl px-4 py-12 sm:px-6 sm:py-16">
      <h1 className="font-display text-3xl font-bold tracking-tight text-fg sm:text-4xl">{title}</h1>
      <p className="mt-2 text-sm text-fg-subtle">Last updated {updated}</p>
      <div className="mt-10 space-y-8 text-[15px] leading-relaxed text-fg-muted [&_a]:text-brand [&_a]:underline [&_h2]:font-display [&_h2]:text-xl [&_h2]:font-bold [&_h2]:text-fg [&_li]:mb-1.5 [&_p]:mt-3 [&_strong]:font-semibold [&_strong]:text-fg [&_ul]:mt-3 [&_ul]:list-disc [&_ul]:pl-5">
        {children}
      </div>
    </article>
  </PublicLayout>
);
