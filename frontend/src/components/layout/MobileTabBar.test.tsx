import { describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';

import { MobileTabBar } from './MobileTabBar';
import { renderWithProviders, screen } from '@/test/render';

describe('MobileTabBar', () => {
  it('carries the league sections when you are inside a league', () => {
    renderWithProviders(<MobileTabBar leagueId="42" onMore={() => {}} />);

    expect(screen.getByText('Overview')).toBeInTheDocument();
    expect(screen.getByText('My Roster')).toBeInTheDocument();
    expect(screen.getByText('Game Plan')).toBeInTheDocument();
  });

  it('falls back to the top-level nav outside a league', () => {
    renderWithProviders(<MobileTabBar onMore={() => {}} />);

    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Leagues')).toBeInTheDocument();
    expect(screen.queryByText('My Roster')).toBeNull();
  });

  it('shows at most four destinations plus More', () => {
    // Five thumb-sized targets is what a 320px screen fits without crowding.
    renderWithProviders(<MobileTabBar leagueId="42" onMore={() => {}} />);

    const links = screen.getAllByRole('link');
    expect(links).toHaveLength(4);
    expect(screen.getByRole('button', { name: 'Open navigation menu' })).toBeInTheDocument();
  });

  it('leaves the rest of the nav to the drawer', () => {
    renderWithProviders(<MobileTabBar leagueId="42" onMore={() => {}} />);
    // Press Box is real nav, just past the cut — it lives behind More.
    expect(screen.queryByText('Press Box')).toBeNull();
  });

  it('opens the drawer from More', async () => {
    const onMore = vi.fn();
    renderWithProviders(<MobileTabBar leagueId="42" onMore={onMore} />);

    await userEvent.click(screen.getByRole('button', { name: 'Open navigation menu' }));
    expect(onMore).toHaveBeenCalledOnce();
  });

  it('treats a setup flow as "not in a league"', () => {
    // /leagues/connect must not render Roster and Trades for a league that
    // does not exist yet.
    renderWithProviders(<MobileTabBar leagueId="connect" onMore={() => {}} />);
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.queryByText('Overview')).toBeNull();
  });

  it('points its links at the league in the route', () => {
    renderWithProviders(<MobileTabBar leagueId="42" onMore={() => {}} />);
    expect(screen.getByRole('link', { name: /My Roster/ })).toHaveAttribute(
      'href',
      '/leagues/42/roster'
    );
  });
});
