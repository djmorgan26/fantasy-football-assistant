import React from 'react';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClientProvider } from 'react-query';

import { useBoardPosts, useReact } from './useBoard';
import { makeQueryClient } from '@/test/render';
import { BoardPost } from '@/types';

const service = vi.hoisted(() => ({
  listPosts: vi.fn(),
  react: vi.fn(),
}));

vi.mock('@/services/board', () => ({ boardService: service }));
vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
}));

const post = (over: Partial<BoardPost> = {}): BoardPost => ({
  id: 1,
  league_id: 1,
  kind: 'post',
  title: null,
  body: 'A post.',
  media_paths: [],
  week: null,
  is_ai: false,
  generated_by: null,
  allow_training: true,
  author_id: 7,
  author_name: 'Demo Manager',
  is_mine: true,
  score: 0,
  reactions: { savage: 0, funny: 0, brutal: 0, smart: 0, cold: 0 },
  my_reactions: [],
  comment_count: 0,
  comments: [],
  created_at: '2026-09-12T20:00:00Z',
  ...over,
});

const wrapper = (client = makeQueryClient()) => {
  const Wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  return { Wrapper, client };
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe('useBoardPosts', () => {
  it('asks for the newest first by default', async () => {
    service.listPosts.mockResolvedValue([post()]);
    const { Wrapper } = wrapper();

    const { result } = renderHook(() => useBoardPosts(1), { wrapper: Wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(service.listPosts).toHaveBeenCalledWith(1, { sort: 'new' });
  });

  it('caches each sort order separately', async () => {
    service.listPosts.mockResolvedValue([]);
    const { Wrapper } = wrapper();

    const { result: newest } = renderHook(() => useBoardPosts(1, 'new'), { wrapper: Wrapper });
    const { result: top } = renderHook(() => useBoardPosts(1, 'top'), { wrapper: Wrapper });

    await waitFor(() => expect(newest.current.isSuccess && top.current.isSuccess).toBe(true));
    expect(service.listPosts).toHaveBeenCalledWith(1, { sort: 'new' });
    expect(service.listPosts).toHaveBeenCalledWith(1, { sort: 'top' });
  });

  it('does not fire without a league', () => {
    const { Wrapper } = wrapper();
    renderHook(() => useBoardPosts(0), { wrapper: Wrapper });
    expect(service.listPosts).not.toHaveBeenCalled();
  });
});

describe('useReact', () => {
  it('patches the updated post into every cached sort order', async () => {
    /*
     * The server returns the whole updated post, so a reaction should not cost
     * a refetch of the feed — tapping through five reactions would otherwise be
     * five round trips.
     */
    const { Wrapper, client } = wrapper();
    const before = [post({ id: 1 }), post({ id: 2 })];
    client.setQueryData(['board', 1, 'new'], before);
    client.setQueryData(['board', 1, 'top'], before);

    const updated = post({ id: 1, score: 3, my_reactions: ['savage'] });
    service.react.mockResolvedValue(updated);

    const { result } = renderHook(() => useReact(1), { wrapper: Wrapper });
    result.current.mutate({ postId: 1, reaction: 'savage' });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    for (const sort of ['new', 'top']) {
      const cached = client.getQueryData<BoardPost[]>(['board', 1, sort])!;
      expect(cached.find((p) => p.id === 1)!.score).toBe(3);
      // The post that was not reacted to is left exactly as it was.
      expect(cached.find((p) => p.id === 2)!.score).toBe(0);
    }
  });

  it('leaves an empty cache empty rather than inserting a stray post', async () => {
    const { Wrapper, client } = wrapper();
    service.react.mockResolvedValue(post({ id: 1, score: 3 }));

    const { result } = renderHook(() => useReact(1), { wrapper: Wrapper });
    result.current.mutate({ postId: 1, reaction: 'savage' });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(client.getQueryData(['board', 1, 'new'])).toEqual([]);
  });

  it('refreshes the voice corpus, because a reaction can change it', async () => {
    const { Wrapper, client } = wrapper();
    const spy = vi.spyOn(client, 'invalidateQueries');
    service.react.mockResolvedValue(post({ id: 1, score: 6 }));

    const { result } = renderHook(() => useReact(1), { wrapper: Wrapper });
    result.current.mutate({ postId: 1, reaction: 'savage' });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(spy).toHaveBeenCalledWith(['board', 1, 'voice-samples']);
    expect(spy).toHaveBeenCalledWith(['board', 1, 'stats']);
  });

  it('surfaces a failure instead of swallowing it', async () => {
    const { Wrapper } = wrapper();
    service.react.mockRejectedValue({ detail: 'nope' });

    const { result } = renderHook(() => useReact(1), { wrapper: Wrapper });
    result.current.mutate({ postId: 1, reaction: 'savage' });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});
