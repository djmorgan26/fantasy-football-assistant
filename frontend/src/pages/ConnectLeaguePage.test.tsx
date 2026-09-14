import { describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';

import { ConnectLeaguePage } from './ConnectLeaguePage';
import { extractLeagueId } from '@/components/connect/EspnConnectForm';
import { renderWithProviders, screen } from '@/test/render';

// The forms reach the network on submit only; mounting them must not.
vi.mock('@/services/api', () => ({
  default: { post: vi.fn(), get: vi.fn() },
}));

describe('ConnectLeaguePage', () => {
  it('offers both platforms, so Sleeper is not hidden behind a second link', () => {
    renderWithProviders(<ConnectLeaguePage />, { route: '/leagues/connect' });

    expect(screen.getByRole('button', { name: /ESPN/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Sleeper/ })).toBeInTheDocument();
  });

  it('starts on ESPN and says so', () => {
    renderWithProviders(<ConnectLeaguePage />, { route: '/leagues/connect' });

    expect(screen.getByRole('button', { name: /ESPN/ })).toHaveAttribute(
      'aria-pressed',
      'true'
    );
    expect(screen.getByLabelText(/League ID or league URL/)).toBeInTheDocument();
  });

  it('swaps in the Sleeper form when Sleeper is picked', async () => {
    const user = userEvent.setup();
    renderWithProviders(<ConnectLeaguePage />, { route: '/leagues/connect' });

    await user.click(screen.getByRole('button', { name: /Sleeper/ }));

    expect(screen.getByLabelText(/Sleeper username/)).toBeInTheDocument();
    expect(screen.queryByLabelText(/League ID or league URL/)).toBeNull();
  });

  it('swaps back to ESPN', async () => {
    const user = userEvent.setup();
    renderWithProviders(<ConnectLeaguePage />, { route: '/leagues/connect' });

    await user.click(screen.getByRole('button', { name: /Sleeper/ }));
    await user.click(screen.getByRole('button', { name: /ESPN/ }));

    expect(screen.getByLabelText(/League ID or league URL/)).toBeInTheDocument();
    expect(screen.queryByLabelText(/Sleeper username/)).toBeNull();
  });

  it('honours the old /leagues/sleeper/connect bookmark', () => {
    renderWithProviders(<ConnectLeaguePage />, { route: '/leagues/sleeper/connect' });

    expect(screen.getByLabelText(/Sleeper username/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Sleeper/ })).toHaveAttribute(
      'aria-pressed',
      'true'
    );
  });

  it('tells you what each platform needs before you pick', () => {
    // The whole point of the picker: Sleeper needs no password, ESPN needs an
    // id. Saying so up front stops someone bouncing off the wrong form.
    renderWithProviders(<ConnectLeaguePage />, { route: '/leagues/connect' });

    expect(screen.getByText(/paste the league link/)).toBeInTheDocument();
    expect(screen.getByText(/no password/)).toBeInTheDocument();
  });
});

describe('extractLeagueId', () => {
  it('reads the id from a query-string league URL', () => {
    expect(
      extractLeagueId('https://fantasy.espn.com/football/team?leagueId=1725275280&teamId=9')
    ).toBe('1725275280');
  });

  it('reads the id from a path-style league URL', () => {
    // ESPN writes the id both ways depending on where the link was copied
    // from, and the path form used to be rejected as "not a valid number".
    expect(
      extractLeagueId('https://fantasy.espn.com/football/league/1725275280')
    ).toBe('1725275280');
  });

  it('passes a bare id straight through', () => {
    expect(extractLeagueId('1725275280')).toBe('1725275280');
    expect(extractLeagueId('  1725275280  ')).toBe('1725275280');
  });

  it('returns nothing for text with no id in it', () => {
    expect(extractLeagueId('https://fantasy.espn.com/football/')).toBe('');
    expect(extractLeagueId('')).toBe('');
  });
});
