import api from './api';
import {
  LeagueNews,
  NewsArticle,
  NewsDigest,
  ScoreboardGame,
  TrendingPlayer,
} from '@/types';

export const newsService = {
  async wire(limit = 30): Promise<NewsArticle[]> {
    const response = await api.get<{ articles: NewsArticle[] }>('/news/wire', {
      params: { limit },
    });
    return response.data.articles;
  },

  /** The wire, annotated with who in this league rosters the player involved. */
  async leagueNews(leagueId: number, limit = 30): Promise<LeagueNews> {
    const response = await api.get<LeagueNews>(`/news/league/${leagueId}`, {
      params: { limit },
    });
    return response.data;
  },

  async digest(leagueId: number, publish = false): Promise<NewsDigest> {
    const response = await api.get<NewsDigest>(`/news/digest/${leagueId}`, {
      params: { publish },
    });
    return response.data;
  },

  async trending(kind: 'add' | 'drop' = 'add', limit = 10): Promise<TrendingPlayer[]> {
    const response = await api.get<{ players: TrendingPlayer[] }>('/news/trending', {
      params: { kind, limit },
    });
    return response.data.players;
  },

  async scoreboard(): Promise<ScoreboardGame[]> {
    const response = await api.get<{ games: ScoreboardGame[] }>('/news/scoreboard');
    return response.data.games;
  },
};
