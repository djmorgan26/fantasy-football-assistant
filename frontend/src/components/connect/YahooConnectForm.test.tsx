import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';

import { renderWithProviders, screen, waitFor } from '@/test/render';
import api, { getAuthToken } from '@/services/api';
import { YahooConnectForm } from './YahooConnectForm';

vi.mock('@/services/api', () => ({
  default: { get: vi.fn(), post: vi.fn() },
  getAuthToken: vi.fn(),
}));

const mockedGet = vi.mocked(api.get);
const mockedPost = vi.mocked(api.post);
const mockedGetAuthToken = vi.mocked(getAuthToken);
const realLocation = window.location;

describe('YahooConnectForm', () => {
  beforeEach(() => {
    mockedGet.mockReset();
    mockedPost.mockReset();
    mockedGetAuthToken.mockReset();
    Object.defineProperty(window, 'location', {
      writable: true,
      value: { origin: 'https://current.fantasy-hub.test', assign: vi.fn() },
    });
  });

  it('sends the saved Fantasy Hub token when the Yahoo form mounts after a platform switch', async () => {
    mockedGetAuthToken.mockReturnValue('fresh-session-token');
    mockedGet.mockResolvedValue({ data: { configured: true, connected: false } });

    renderWithProviders(<YahooConnectForm />);

    await waitFor(() => expect(mockedGet).toHaveBeenCalledWith('/yahoo/status', {
      headers: { 'X-Fantasy-Session': 'fresh-session-token' },
    }));
  });

  afterEach(() => {
    Object.defineProperty(window, 'location', { writable: true, value: realLocation });
    vi.restoreAllMocks();
  });

  it('explains that Yahoo sign-in attaches a league to the existing account', async () => {
    mockedGet.mockResolvedValue({ data: { configured: true, connected: false } });

    renderWithProviders(<YahooConnectForm />);

    expect(await screen.findByText(/Sign in to Yahoo to add this league to your account/)).toBeInTheDocument();
    expect(screen.getByText(/not another Fantasy Hub login/)).toBeInTheDocument();
  });

  it('sends Yahoo back to the same browser origin when starting authorization', async () => {
    mockedGet.mockResolvedValue({ data: { configured: true, connected: false } });
    mockedPost.mockResolvedValue({ data: { authorization_url: 'https://login.yahoo.com/authorize' } });
    const user = userEvent.setup();

    renderWithProviders(<YahooConnectForm />);
    await user.click(await screen.findByRole('button', { name: 'Sign in to Yahoo' }));

    expect(mockedPost).toHaveBeenCalledWith('/yahoo/authorize', {
      return_to: 'https://current.fantasy-hub.test',
    });
    expect(window.location.assign).toHaveBeenCalledWith('https://login.yahoo.com/authorize');
  });

  it('identifies a connected Yahoo account that has no fantasy leagues and offers account switching', async () => {
    mockedGet
      .mockResolvedValueOnce({ data: { configured: true, connected: true } })
      .mockResolvedValueOnce({ data: [] });
    mockedPost.mockResolvedValue({ data: { authorization_url: 'https://login.yahoo.com/authorize' } });
    const user = userEvent.setup();

    renderWithProviders(<YahooConnectForm />);

    expect(await screen.findByText(/this Yahoo account has no Fantasy Football leagues/)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Use another Yahoo account' }));
    await waitFor(() => expect(mockedPost).toHaveBeenCalledWith('/yahoo/authorize', {
      return_to: 'https://current.fantasy-hub.test',
    }));
  });

  it('connects the selected Yahoo league', async () => {
    mockedGet
      .mockResolvedValueOnce({ data: { configured: true, connected: true } })
      .mockResolvedValueOnce({ data: [{ league_key: 'nfl.l.1', name: 'Sunday League', season: 2026, num_teams: 12 }] });
    mockedPost.mockResolvedValue({ data: { message: 'Connected to Sunday League' } });
    const user = userEvent.setup();

    renderWithProviders(<YahooConnectForm />);
    await user.click(await screen.findByRole('button', { name: /Sunday League/ }));

    expect(mockedPost).toHaveBeenCalledWith('/yahoo/connect', { league_key: 'nfl.l.1' });
  });
});
