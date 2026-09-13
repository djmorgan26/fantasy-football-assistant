import { describe, expect, it, vi, beforeEach } from 'vitest';

import { boardService } from './board';
import { newsService } from './news';
import { assistantService } from './assistant';
import api from './api';

/**
 * These services are thin, which is the point: the only thing that can be
 * wrong is the URL or the payload shape, and both are easy to get wrong in a
 * way no type check catches.
 */
vi.mock('./api', () => ({
  default: {
    get: vi.fn(() => Promise.resolve({ data: {} })),
    post: vi.fn(() => Promise.resolve({ data: {} })),
    patch: vi.fn(() => Promise.resolve({ data: {} })),
    delete: vi.fn(() => Promise.resolve({ data: {} })),
  },
}));

const mocked = api as unknown as {
  get: ReturnType<typeof vi.fn>;
  post: ReturnType<typeof vi.fn>;
  patch: ReturnType<typeof vi.fn>;
  delete: ReturnType<typeof vi.fn>;
};

beforeEach(() => {
  vi.clearAllMocks();
  mocked.get.mockResolvedValue({ data: {} });
  mocked.post.mockResolvedValue({ data: {} });
  mocked.patch.mockResolvedValue({ data: {} });
  mocked.delete.mockResolvedValue({ data: {} });
});

describe('boardService', () => {
  it('defaults the feed to newest first', async () => {
    mocked.get.mockResolvedValue({ data: [] });
    await boardService.listPosts(7);

    expect(mocked.get).toHaveBeenCalledWith('/board/7/posts', {
      params: { sort: 'new', kind: undefined },
    });
  });

  it('passes the sort and kind through', async () => {
    mocked.get.mockResolvedValue({ data: [] });
    await boardService.listPosts(7, { sort: 'top', kind: 'weekly_recap' });

    expect(mocked.get).toHaveBeenCalledWith('/board/7/posts', {
      params: { sort: 'top', kind: 'weekly_recap' },
    });
  });

  it('posts a reaction to the right post', async () => {
    await boardService.react(7, 42, 'savage');
    expect(mocked.post).toHaveBeenCalledWith('/board/7/posts/42/reactions', {
      reaction: 'savage',
    });
  });

  it('sends a comment body', async () => {
    await boardService.comment(7, 42, 'Filing a counter-complaint.');
    expect(mocked.post).toHaveBeenCalledWith('/board/7/posts/42/comments', {
      body: 'Filing a counter-complaint.',
    });
  });

  it('patches only the training flag when opting a post out', async () => {
    await boardService.setTraining(7, 42, false);
    expect(mocked.patch).toHaveBeenCalledWith('/board/7/posts/42', {
      allow_training: false,
    });
  });

  it('deletes by id', async () => {
    await boardService.deletePost(7, 42);
    expect(mocked.delete).toHaveBeenCalledWith('/board/7/posts/42');
  });
});

describe('newsService', () => {
  it('unwraps the articles envelope', async () => {
    mocked.get.mockResolvedValue({ data: { articles: [{ id: '1' }] } });
    expect(await newsService.wire()).toEqual([{ id: '1' }]);
  });

  it('unwraps the players envelope for trending', async () => {
    mocked.get.mockResolvedValue({ data: { players: [{ name: 'A' }] } });
    expect(await newsService.trending()).toEqual([{ name: 'A' }]);
  });

  it('asks for adds by default', async () => {
    mocked.get.mockResolvedValue({ data: { players: [] } });
    await newsService.trending();
    expect(mocked.get).toHaveBeenCalledWith('/news/trending', {
      params: { kind: 'add', limit: 10 },
    });
  });

  it('does not publish the digest unless asked', async () => {
    mocked.get.mockResolvedValue({ data: { digest: '', items: [] } });
    await newsService.digest(7);
    expect(mocked.get).toHaveBeenCalledWith('/news/digest/7', {
      params: { publish: false },
    });
  });

  it('publishes the digest when asked', async () => {
    mocked.get.mockResolvedValue({ data: { digest: '', items: [] } });
    await newsService.digest(7, true);
    expect(mocked.get).toHaveBeenCalledWith('/news/digest/7', {
      params: { publish: true },
    });
  });

  it('keeps the league news envelope, which carries the rostered count', async () => {
    mocked.get.mockResolvedValue({
      data: { articles: [], rostered_count: 3, league_name: 'X' },
    });
    expect((await newsService.leagueNews(7)).rostered_count).toBe(3);
  });
});

describe('assistantService', () => {
  it('sends only the recent tail of the conversation', async () => {
    mocked.post.mockResolvedValue({ data: { reply: '', generated_by: '', grounded_on: [] } });

    const history = Array.from({ length: 10 }, (_, i) => ({
      role: 'user' as const,
      content: `turn-${i}`,
    }));
    await assistantService.chat(7, 'And now?', history);

    const sent = mocked.post.mock.calls[0][1];
    expect(sent.message).toBe('And now?');
    expect(sent.history).toHaveLength(6);
    expect(sent.history[0].content).toBe('turn-4');
  });

  it('sends an empty history on the first turn', async () => {
    mocked.post.mockResolvedValue({ data: { reply: '', generated_by: '', grounded_on: [] } });
    await assistantService.chat(7, 'Hello');
    expect(mocked.post.mock.calls[0][1].history).toEqual([]);
  });

  it('unwraps the suggestions envelope', async () => {
    mocked.get.mockResolvedValue({ data: { suggestions: ['a', 'b'] } });
    expect(await assistantService.suggestions(7)).toEqual(['a', 'b']);
  });

  it('fetches the primer for the right league', async () => {
    mocked.get.mockResolvedValue({ data: { week: 1 } });
    await assistantService.primer(7);
    expect(mocked.get).toHaveBeenCalledWith('/assistant/7/primer');
  });
});
