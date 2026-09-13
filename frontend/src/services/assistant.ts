import api from './api';
import { ChatReply, ChatTurn, WeeklyPrimer } from '@/types';

export const assistantService = {
  async chat(leagueId: number, message: string, history: ChatTurn[] = []): Promise<ChatReply> {
    const response = await api.post<ChatReply>(`/assistant/${leagueId}/chat`, {
      message,
      // Keep the tail only: the backend caps it anyway and a long history
      // crowds out the grounding facts in the prompt.
      history: history.slice(-6),
    });
    return response.data;
  },

  async suggestions(leagueId: number): Promise<string[]> {
    const response = await api.get<{ suggestions: string[] }>(
      `/assistant/${leagueId}/suggestions`
    );
    return response.data.suggestions;
  },

  async primer(leagueId: number): Promise<WeeklyPrimer> {
    const response = await api.get<WeeklyPrimer>(`/assistant/${leagueId}/primer`);
    return response.data;
  },
};
