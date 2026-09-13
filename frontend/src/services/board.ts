import api from './api';
import {
  BoardComment,
  BoardPost,
  BoardStats,
  PostKind,
  ReactionKind,
  VoiceSample,
} from '@/types';

export interface NewPost {
  body: string;
  title?: string;
  kind?: PostKind;
  week?: number;
  allow_training?: boolean;
}

export const boardService = {
  async listPosts(
    leagueId: number,
    opts: { sort?: 'new' | 'top'; kind?: PostKind } = {}
  ): Promise<BoardPost[]> {
    const response = await api.get<BoardPost[]>(`/board/${leagueId}/posts`, {
      params: { sort: opts.sort ?? 'new', kind: opts.kind },
    });
    return response.data;
  },

  async createPost(leagueId: number, post: NewPost): Promise<BoardPost> {
    const response = await api.post<BoardPost>(`/board/${leagueId}/posts`, post);
    return response.data;
  },

  async deletePost(leagueId: number, postId: number): Promise<void> {
    await api.delete(`/board/${leagueId}/posts/${postId}`);
  },

  /** Tap once to react, tap the same one again to take it back. */
  async react(leagueId: number, postId: number, reaction: ReactionKind): Promise<BoardPost> {
    const response = await api.post<BoardPost>(
      `/board/${leagueId}/posts/${postId}/reactions`,
      { reaction }
    );
    return response.data;
  },

  async comment(leagueId: number, postId: number, body: string): Promise<BoardComment> {
    const response = await api.post<BoardComment>(
      `/board/${leagueId}/posts/${postId}/comments`,
      { body }
    );
    return response.data;
  },

  async setTraining(leagueId: number, postId: number, allow: boolean): Promise<BoardPost> {
    const response = await api.patch<BoardPost>(`/board/${leagueId}/posts/${postId}`, {
      allow_training: allow,
    });
    return response.data;
  },

  async voiceSamples(leagueId: number): Promise<VoiceSample[]> {
    const response = await api.get<VoiceSample[]>(`/board/${leagueId}/voice-samples`);
    return response.data;
  },

  async stats(leagueId: number): Promise<BoardStats> {
    const response = await api.get<BoardStats>(`/board/${leagueId}/stats`);
    return response.data;
  },
};
