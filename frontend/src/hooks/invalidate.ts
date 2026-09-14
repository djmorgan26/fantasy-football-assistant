import { QueryClient } from 'react-query';

/**
 * What goes stale when your standing in a league changes.
 *
 * Claiming a team, connecting a league, or syncing it changes the answer to
 * "which team is mine", and most league pages are built on that answer rather
 * than on the league itself. They used to keep serving the old answer until
 * their own staleTime expired (two to five minutes), so right after claiming a
 * team the roster was yours but Game Plan, the primer, Game Day, the news feed
 * and the cross-league view were all still describing the previous one.
 *
 * Co-owned teams made this visible rather than merely wrong: two managers can
 * now hold the same team, so a claim legitimately changes your view without
 * changing anything another viewer would see, and nothing else would have told
 * these caches to refetch.
 *
 * Keyed by league where the query is, so one league's refresh does not throw
 * away another's.
 */
export const invalidateLeagueIdentity = (client: QueryClient, leagueId?: number) => {
  const scoped = (key: string) =>
    leagueId ? [key, leagueId] : [key];

  // Who is in the league, and which team is mine.
  client.invalidateQueries('leagues');
  client.invalidateQueries(scoped('league'));
  client.invalidateQueries(scoped('teams'));

  // Everything derived from "my team".
  client.invalidateQueries(scoped('action-plan'));
  client.invalidateQueries(scoped('assistant'));
  client.invalidateQueries(scoped('gameday'));
  client.invalidateQueries(scoped('draft'));
  client.invalidateQueries(scoped('waiver-budgets'));
  client.invalidateQueries(['news', 'league', ...(leagueId ? [leagueId] : [])]);

  // Rosters are keyed by team id, so the claim can move to a team whose roster
  // was never fetched. Drop them all rather than guess which one.
  client.invalidateQueries(['roster']);
  client.invalidateQueries(['team']);

  // The cross-league view is built from every league's "my team" at once, so
  // it is stale no matter which league changed.
  client.invalidateQueries(['portfolio']);
};
