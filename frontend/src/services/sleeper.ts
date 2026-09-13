import api from './api';

export interface SleeperLeagueSummary {
  league_id: string;
  name: string;
  season: string;
  total_rosters: number;
  status?: string;
  avatar?: string | null;
}

export interface SleeperUserLeagues {
  user_id: string;
  username: string;
  season: number;
  leagues: SleeperLeagueSummary[];
}

export const sleeperService = {
  /**
   * Every league a username is in for a season.
   *
   * Sleeper's API is public and read-only, so this needs no password and no
   * token — a username is enough to find someone's leagues.
   */
  async findLeagues(username: string, season: number): Promise<SleeperUserLeagues> {
    const response = await api.get<SleeperUserLeagues>(
      `/sleeper/user/${encodeURIComponent(username)}/leagues/${season}`
    );
    return response.data;
  },

  async connect(leagueId: string, username: string) {
    const response = await api.post('/sleeper/connect', {
      league_id: leagueId,
      sleeper_user_id: username,
    });
    return response.data;
  },
};
