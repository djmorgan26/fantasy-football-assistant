import api from './api';
import {
  ContentProfile,
  ContentType,
  GeneratedContent,
  WeeklyNarrative,
} from '@/types';

export const contentService = {
  async getProfile(leagueId: number): Promise<ContentProfile> {
    const response = await api.get<ContentProfile>(`/content/${leagueId}/profile`);
    return response.data;
  },

  async updateProfile(
    leagueId: number,
    profile: Omit<ContentProfile, 'league_id'>
  ): Promise<ContentProfile> {
    const response = await api.put<ContentProfile>(`/content/${leagueId}/profile`, profile);
    return response.data;
  },

  async getNarrative(leagueId: number, week: number): Promise<WeeklyNarrative> {
    const response = await api.get<WeeklyNarrative>(
      `/content/${leagueId}/narrative/week/${week}`
    );
    return response.data;
  },

  async generate(
    leagueId: number,
    contentType: ContentType,
    week?: number
  ): Promise<GeneratedContent> {
    const response = await api.post<GeneratedContent>(`/content/${leagueId}/generate`, {
      content_type: contentType,
      week,
    });
    return response.data;
  },
};
