import { describe, expect, it, vi } from 'vitest';
import { QueryClient } from 'react-query';

import { invalidateLeagueIdentity } from './invalidate';

/**
 * Claiming a team changes the answer to "which team is mine", and most league
 * pages are built on that answer rather than on the league itself. Before
 * this, only the team list refetched, so Game Plan, the primer, Game Day, the
 * news feed and the cross-league view kept describing the previous team until
 * their own staleTime ran out.
 */
describe('invalidateLeagueIdentity', () => {
  const run = (leagueId?: number) => {
    const client = new QueryClient();
    const spy = vi.spyOn(client, 'invalidateQueries');
    invalidateLeagueIdentity(client, leagueId);
    return spy.mock.calls.map(([key]) => JSON.stringify(key));
  };

  it('refreshes every page built on "which team is mine"', () => {
    const calls = run(7);

    for (const key of [
      ['action-plan', 7],
      ['assistant', 7],
      ['gameday', 7],
      ['draft', 7],
      ['waiver-budgets', 7],
      ['news', 'league', 7],
      ['teams', 7],
      ['league', 7],
    ]) {
      expect(calls).toContain(JSON.stringify(key));
    }
  });

  it('refreshes the cross-league view, which spans every league at once', () => {
    expect(run(7)).toContain(JSON.stringify(['portfolio']));
  });

  it('drops rosters, since the claim can move to a team never fetched', () => {
    const calls = run(7);
    expect(calls).toContain(JSON.stringify(['roster']));
    expect(calls).toContain(JSON.stringify(['team']));
  });

  it('scopes to one league so another league is not thrown away', () => {
    const calls = run(7);
    expect(calls).not.toContain(JSON.stringify(['action-plan']));
    expect(calls).toContain(JSON.stringify(['action-plan', 7]));
  });

  it('falls back to every league when the id is unknown', () => {
    // Disconnect and connect responses do not always carry a league id.
    const calls = run(undefined);
    expect(calls).toContain(JSON.stringify(['action-plan']));
    expect(calls).toContain(JSON.stringify(['news', 'league']));
  });
});
