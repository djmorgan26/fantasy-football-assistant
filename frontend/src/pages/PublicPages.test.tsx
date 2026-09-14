import { describe, expect, it } from 'vitest';

import { LandingPage } from './LandingPage';
import { PrivacyPage } from './PrivacyPage';
import { TermsPage } from './TermsPage';
import { renderWithProviders, screen, within } from '@/test/render';

/**
 * These pages exist so a signed-out visitor, and Google's consent screen, can
 * reach them. The render helper deliberately provides no AuthProvider, so
 * anything here that reached for auth state would throw: that is the point of
 * the suite, not an oversight.
 */
describe('public pages', () => {
  describe('Privacy Policy', () => {
    it('renders with no account and no auth context', () => {
      renderWithProviders(<PrivacyPage />);
      expect(screen.getByRole('heading', { name: 'Privacy Policy', level: 1 })).toBeInTheDocument();
    });

    it('links the Google API Services User Data Policy', () => {
      // Google requires this disclosure from any app using their sign-in.
      renderWithProviders(<PrivacyPage />);
      const link = screen.getByRole('link', { name: /Google API Services User Data Policy/i });
      expect(link).toHaveAttribute(
        'href',
        'https://developers.google.com/terms/api-services-user-data-policy'
      );
    });

    it('says how to delete an account', () => {
      renderWithProviders(<PrivacyPage />);
      expect(screen.getByRole('heading', { name: /Keeping and deleting it/i })).toBeInTheDocument();
      expect(
        screen.getAllByRole('link', { name: 'davidjmorgan26@gmail.com' }).length
      ).toBeGreaterThan(0);
    });

    it('states plainly that there are no trackers', () => {
      renderWithProviders(<PrivacyPage />);
      expect(screen.getByText(/no third-party trackers in this app at all/i)).toBeInTheDocument();
    });
  });

  describe('Terms of Service', () => {
    it('renders with no account', () => {
      renderWithProviders(<TermsPage />);
      expect(screen.getByRole('heading', { name: 'Terms of Service', level: 1 })).toBeInTheDocument();
    });

    it('warns that generated advice can be wrong', () => {
      // The app hands out lineup calls from a language model. Saying so is the
      // honest part of these terms, so it should not quietly disappear.
      renderWithProviders(<TermsPage />);
      expect(
        screen.getByRole('heading', { name: /Advice is a suggestion, not a guarantee/i })
      ).toBeInTheDocument();
    });

    it('disclaims affiliation with ESPN, Sleeper and the NFL', () => {
      renderWithProviders(<TermsPage />);
      expect(
        screen.getByRole('heading', { name: /Not affiliated with ESPN, Sleeper or the NFL/i })
      ).toBeInTheDocument();
    });
  });

  describe('Landing page', () => {
    it('offers both sign in and sign up', () => {
      renderWithProviders(<LandingPage />);
      expect(screen.getByRole('link', { name: 'Create an account' })).toHaveAttribute(
        'href',
        '/register'
      );
      expect(screen.getAllByRole('link', { name: 'Sign in' })[0]).toHaveAttribute('href', '/login');
    });

    it('describes what the app does, which is what Google asks a home page to do', () => {
      renderWithProviders(<LandingPage />);
      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(/fantasy football/i);
      expect(screen.getByRole('heading', { name: 'Both platforms, one place' })).toBeInTheDocument();
    });
  });

  describe('shared footer', () => {
    it.each([
      ['landing', <LandingPage key="l" />],
      ['privacy', <PrivacyPage key="p" />],
      ['terms', <TermsPage key="t" />],
    ])('links privacy and terms from the %s page', (_name, element) => {
      renderWithProviders(element);
      const footer = screen.getByRole('contentinfo');
      expect(within(footer).getByRole('link', { name: 'Privacy' })).toHaveAttribute(
        'href',
        '/privacy'
      );
      expect(within(footer).getByRole('link', { name: 'Terms' })).toHaveAttribute('href', '/terms');
    });
  });
});
