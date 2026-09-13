import { useMutation, useQuery, useQueryClient } from 'react-query';
import toast from 'react-hot-toast';

import { ApiError, BoardPost, BoardStats, ReactionKind, VoiceSample } from '@/types';
import { boardService, NewPost } from '@/services/board';

const feedKey = (leagueId: number, sort: string) => ['board', leagueId, sort];

export const useBoardPosts = (leagueId: number, sort: 'new' | 'top' = 'new') =>
  useQuery<BoardPost[], ApiError>(
    feedKey(leagueId, sort),
    () => boardService.listPosts(leagueId, { sort }),
    { enabled: !!leagueId, staleTime: 15 * 1000 }
  );

export const useCreatePost = (leagueId: number) => {
  const queryClient = useQueryClient();
  return useMutation<BoardPost, ApiError, NewPost>(
    (post) => boardService.createPost(leagueId, post),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['board', leagueId]);
        toast.success('Posted');
      },
      onError: (error) => { toast.error(error.detail || "That post didn't go through"); },
    }
  );
};

export const useDeletePost = (leagueId: number) => {
  const queryClient = useQueryClient();
  return useMutation<void, ApiError, number>(
    (postId) => boardService.deletePost(leagueId, postId),
    {
      onSuccess: () => { queryClient.invalidateQueries(['board', leagueId]); },
      onError: (error) => { toast.error(error.detail || "Couldn't delete that post"); },
    }
  );
};

export const useReact = (leagueId: number) => {
  const queryClient = useQueryClient();
  return useMutation<BoardPost, ApiError, { postId: number; reaction: ReactionKind }>(
    ({ postId, reaction }) => boardService.react(leagueId, postId, reaction),
    {
      // The server returns the whole updated post, so patch it into every
      // cached sort order rather than refetching the feed on each tap.
      onSuccess: (updated) => {
        (['new', 'top'] as const).forEach((sort) => {
          queryClient.setQueryData<BoardPost[]>(feedKey(leagueId, sort), (posts) =>
            (posts ?? []).map((p) => (p.id === updated.id ? updated : p))
          );
        });
        queryClient.invalidateQueries(['board', leagueId, 'voice-samples']);
        queryClient.invalidateQueries(['board', leagueId, 'stats']);
      },
      onError: (error) => { toast.error(error.detail || "That reaction didn't stick"); },
    }
  );
};

export const useComment = (leagueId: number) => {
  const queryClient = useQueryClient();
  return useMutation<unknown, ApiError, { postId: number; body: string }>(
    ({ postId, body }) => boardService.comment(leagueId, postId, body),
    {
      onSuccess: () => { queryClient.invalidateQueries(['board', leagueId]); },
      onError: (error) => { toast.error(error.detail || "Couldn't post that comment"); },
    }
  );
};

export const useSetTraining = (leagueId: number) => {
  const queryClient = useQueryClient();
  return useMutation<BoardPost, ApiError, { postId: number; allow: boolean }>(
    ({ postId, allow }) => boardService.setTraining(leagueId, postId, allow),
    {
      onSuccess: (updated) => {
        queryClient.invalidateQueries(['board', leagueId]);
        toast.success(
          updated.allow_training
            ? 'This post can teach the AI again'
            : "This post is out of the AI's training"
        );
      },
      onError: (error) => { toast.error(error.detail || "Couldn't change that"); },
    }
  );
};

export const useVoiceSamples = (leagueId: number) =>
  useQuery<VoiceSample[], ApiError>(
    ['board', leagueId, 'voice-samples'],
    () => boardService.voiceSamples(leagueId),
    { enabled: !!leagueId }
  );

export const useBoardStats = (leagueId: number) =>
  useQuery<BoardStats, ApiError>(
    ['board', leagueId, 'stats'],
    () => boardService.stats(leagueId),
    { enabled: !!leagueId }
  );
