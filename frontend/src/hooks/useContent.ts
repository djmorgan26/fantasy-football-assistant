import { useQuery, useMutation, useQueryClient } from 'react-query';
import {
  ContentProfile,
  ContentType,
  GeneratedContent,
  ApiError,
} from '@/types';
import { contentService } from '@/services/content';
import toast from 'react-hot-toast';

export const useContentProfile = (leagueId: number, enabled = true) => {
  return useQuery<ContentProfile, ApiError>(
    ['content', 'profile', leagueId],
    () => contentService.getProfile(leagueId),
    {
      enabled: enabled && !!leagueId,
      staleTime: 5 * 60 * 1000,
      onError: (error) => {
        toast.error(error.detail || 'Failed to load voice profile');
      },
    }
  );
};

export const useUpdateContentProfile = (leagueId: number) => {
  const queryClient = useQueryClient();
  return useMutation<ContentProfile, ApiError, Omit<ContentProfile, 'league_id'>>(
    (profile) => contentService.updateProfile(leagueId, profile),
    {
      onSuccess: (data) => {
        queryClient.setQueryData(['content', 'profile', leagueId], data);
        toast.success('Voice profile saved');
      },
      onError: (error) => {
        toast.error(error.detail || 'Failed to save voice profile');
      },
    }
  );
};

export const useGenerateContent = (leagueId: number) => {
  return useMutation<
    GeneratedContent,
    ApiError,
    { contentType: ContentType; week?: number }
  >(
    ({ contentType, week }) => contentService.generate(leagueId, contentType, week),
    {
      onError: (error) => {
        toast.error(error.detail || 'Failed to generate content');
      },
    }
  );
};
