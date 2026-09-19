import { describe, expect, it, vi, beforeEach } from 'vitest';
import { waitFor } from '@testing-library/react';

import { StrategicSuggestions } from './StrategicSuggestions';
import { render, screen } from '@/test/render';
import { StrategicSuggestion } from '@/types';

const get = vi.hoisted(() => vi.fn());
vi.mock('@/services/api', () => ({ default: { get } }));

const suggestion = (over: Partial<StrategicSuggestion> = {}): StrategicSuggestion =>
  ({
    id: '1',
    type: 'pickup',
    priority: 'high',
    title: 'Add Jalen Coker',
    description: 'He out-projects your weakest starter.',
    ...over,
  }) as StrategicSuggestion;

beforeEach(() => {
  get.mockReset();
  get.mockResolvedValue({ data: [suggestion()] });
});

describe('StrategicSuggestions', () => {
  it('reads as loading, not as an error, while the team lookup is in flight', async () => {
    // Which team is mine takes two requests on the page above. Treating the
    // gap as "no team selected" put a red error on screen on every visit.
    const { container } = render(
      <StrategicSuggestions leagueId={1} userTeamId={undefined} resolvingTeam />
    );

    expect(screen.queryByText('Unable to Load Suggestions')).toBeNull();
    expect(container.querySelectorAll('.animate-pulse').length).toBeGreaterThan(0);
  });

  it('asks nothing of the API until it knows which team to ask about', () => {
    render(<StrategicSuggestions leagueId={1} userTeamId={undefined} resolvingTeam />);
    expect(get).not.toHaveBeenCalled();
  });

  it('says to claim a team once the lookup has finished and found none', async () => {
    render(<StrategicSuggestions leagueId={1} userTeamId={undefined} />);

    expect(await screen.findByText('Claim your team first')).toBeInTheDocument();
    // Not an error: nothing failed, there is simply nothing to advise on.
    expect(screen.queryByText('Unable to Load Suggestions')).toBeNull();
  });

  it('fetches and lists suggestions once the team is known', async () => {
    render(<StrategicSuggestions leagueId={1} userTeamId={42} />);

    expect(await screen.findByText('Add Jalen Coker')).toBeInTheDocument();
    expect(get).toHaveBeenCalledWith('/suggestions/1/42');
  });

  it('reports a real failure as a failure', async () => {
    get.mockRejectedValue({ detail: 'Upstream is down' });
    render(<StrategicSuggestions leagueId={1} userTeamId={42} />);

    expect(await screen.findByText('Unable to Load Suggestions')).toBeInTheDocument();
    expect(screen.getByText('Upstream is down')).toBeInTheDocument();
  });

  it('offers a refresh only once there is a team to refresh for', async () => {
    const { rerender } = render(
      <StrategicSuggestions leagueId={1} userTeamId={undefined} resolvingTeam />
    );
    expect(screen.queryByRole('button', { name: /Refresh Suggestions/ })).toBeNull();

    rerender(<StrategicSuggestions leagueId={1} userTeamId={42} />);
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /Refresh Suggestions/ })).toBeEnabled()
    );
  });
});
