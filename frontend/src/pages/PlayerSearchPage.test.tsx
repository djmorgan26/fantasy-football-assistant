import { describe, expect, it, vi, beforeEach } from 'vitest';
import userEvent from '@testing-library/user-event';

import { PlayerSearchPage } from './PlayerSearchPage';
import { renderWithProviders, screen } from '@/test/render';

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return { ...actual, useParams: () => ({ leagueId: '1' }) };
});

vi.mock('@/hooks/useLeagues', () => ({
  useLeague: () => ({ data: { id: 1, name: 'The Sunday Scaries Dynasty', current_week: 14 } }),
}));

const search = vi.hoisted(() => ({
  data: undefined as { players: unknown[]; total_count: number } | undefined,
  isLoading: false,
  error: undefined as unknown,
  enabledWith: [] as boolean[],
}));

vi.mock('@/hooks/usePlayers', () => ({
  useSearchPlayers: (_request: unknown, enabled: boolean) => {
    search.enabledWith.push(enabled);
    return search;
  },
}));

beforeEach(() => {
  search.data = undefined;
  search.isLoading = false;
  search.error = undefined;
  search.enabledWith = [];
});

describe('PlayerSearchPage', () => {
  it('prompts for a search rather than reporting one that never ran', () => {
    // "No Players Found — try adjusting your search criteria" on an untouched
    // form reads as a search that came back empty. Nothing has been asked yet.
    renderWithProviders(<PlayerSearchPage />);

    expect(screen.getByText('Search for a player')).toBeInTheDocument();
    expect(screen.queryByText('No Players Found')).toBeNull();
  });

  it('asks the API nothing until you press Search', () => {
    renderWithProviders(<PlayerSearchPage />);
    expect(search.enabledWith.every((on) => on === false)).toBe(true);
  });

  it('stands in for the results while the search runs', async () => {
    const { container } = renderWithProviders(<PlayerSearchPage />);
    search.isLoading = true;

    await userEvent.click(screen.getByRole('button', { name: /Search Players/ }));

    expect(container.querySelectorAll('.animate-pulse').length).toBeGreaterThan(0);
    expect(screen.queryByText('No Players Found')).toBeNull();
  });

  it('reports an empty result once a search has actually run', async () => {
    search.data = { players: [], total_count: 0 };
    renderWithProviders(<PlayerSearchPage />);

    await userEvent.click(screen.getByRole('button', { name: /Search Players/ }));
    expect(screen.getByText('No Players Found')).toBeInTheDocument();
  });
});
