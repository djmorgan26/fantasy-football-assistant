import { describe, expect, it, vi, beforeEach } from 'vitest';
import userEvent from '@testing-library/user-event';

import { BoardPage } from './BoardPage';
import { renderWithProviders, screen, waitFor, within } from '@/test/render';
import { BoardPost, VoiceSample } from '@/types';

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return { ...actual, useParams: () => ({ leagueId: '1' }) };
});

vi.mock('@/hooks/useLeagues', () => ({
  useLeague: () => ({ data: { id: 1, name: 'The Sunday Scaries Dynasty' } }),
}));

const state = vi.hoisted(() => ({
  posts: [] as BoardPost[],
  samples: [] as VoiceSample[],
  stats: { posts: 0, comments: 0, reactions: 0, voice_samples: 0, top_reaction: null },
  createPost: vi.fn(),
  react: vi.fn(),
  digestMutate: vi.fn(),
  digestData: undefined as { digest: string; generated_by: string } | undefined,
}));

vi.mock('@/hooks/useBoard', () => ({
  useBoardPosts: () => ({ data: state.posts, isLoading: false }),
  useBoardStats: () => ({ data: state.stats }),
  useVoiceSamples: () => ({ data: state.samples }),
  useCreatePost: () => ({ mutate: state.createPost, isLoading: false }),
  useReact: () => ({ mutate: state.react, isLoading: false }),
  useComment: () => ({ mutate: vi.fn(), isLoading: false }),
  useDeletePost: () => ({ mutate: vi.fn() }),
  useSetTraining: () => ({ mutate: vi.fn() }),
}));

vi.mock('@/hooks/useNews', () => ({
  useDigest: () => ({
    mutate: state.digestMutate,
    isLoading: false,
    data: state.digestData,
  }),
}));

const post = (over: Partial<BoardPost> = {}): BoardPost => ({
  id: 1,
  league_id: 1,
  kind: 'post',
  title: null,
  body: 'Bench Warmers Anonymous started a kicker on bye and still won by thirty.',
  media_paths: [],
  week: 14,
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

beforeEach(() => {
  state.posts = [];
  state.samples = [];
  state.stats = { posts: 0, comments: 0, reactions: 0, voice_samples: 0, top_reaction: null };
  state.createPost = vi.fn();
  state.react = vi.fn();
  state.digestMutate = vi.fn();
  state.digestData = undefined;
});

describe('BoardPage', () => {
  it('invites the first post when the board is empty', () => {
    renderWithProviders(<BoardPage />);
    expect(screen.getByText('Nothing on the board yet')).toBeInTheDocument();
  });

  it('explains why reacting matters', () => {
    // Nobody reacts to things unless the payoff is visible.
    renderWithProviders(<BoardPage />);
    expect(screen.getByText(/teach the AI your voice/i)).toBeInTheDocument();
  });

  it('publishes what you type', async () => {
    renderWithProviders(<BoardPage />);

    await userEvent.type(
      screen.getByPlaceholderText('What happened this week?'),
      'Filing a complaint.'
    );
    await userEvent.click(screen.getByRole('button', { name: 'Post' }));

    expect(state.createPost).toHaveBeenCalledWith(
      { body: 'Filing a complaint.' },
      expect.anything()
    );
  });

  it('will not publish an empty post', async () => {
    renderWithProviders(<BoardPage />);
    expect(screen.getByRole('button', { name: 'Post' })).toBeDisabled();
    expect(state.createPost).not.toHaveBeenCalled();
  });

  it('lists the posts it was given', () => {
    state.posts = [post({ id: 1 }), post({ id: 2, body: 'A second post entirely.' })];
    renderWithProviders(<BoardPage />);

    expect(screen.getByText(/Bench Warmers Anonymous/)).toBeInTheDocument();
    expect(screen.getByText('A second post entirely.')).toBeInTheDocument();
  });

  it('sends a reaction from a post card', async () => {
    state.posts = [post()];
    renderWithProviders(<BoardPage />);

    await userEvent.click(screen.getByRole('button', { name: 'React: Savage' }));
    expect(state.react).toHaveBeenCalledWith({ postId: 1, reaction: 'savage' });
  });

  it('shows what the AI has learned so far', () => {
    state.samples = [
      { id: 1, title: null, text: 'A post they loved.', score: 8, tags: ['funny'],
        author_name: 'Demo Manager' },
    ];
    renderWithProviders(<BoardPage />);

    const panel = screen.getByText('What the AI learned').closest('div')!.parentElement!;
    expect(within(panel).getByText('A post they loved.')).toBeInTheDocument();
    expect(within(panel).getByText('+8')).toBeInTheDocument();
  });

  it('names the score a post needs before it teaches anything', () => {
    renderWithProviders(<BoardPage />);
    expect(screen.getByText('+4')).toBeInTheDocument();
  });

  it('publishes the digest to the board on request', async () => {
    renderWithProviders(<BoardPage />);
    await userEvent.click(screen.getByRole('button', { name: /Post today's digest/ }));
    expect(state.digestMutate).toHaveBeenCalledWith({ publish: true });
  });

  it('says when the digest is facts-only', () => {
    state.digestData = { digest: 'Quiet day.', generated_by: 'fallback' };
    renderWithProviders(<BoardPage />);
    expect(screen.getByText(/no AI writer configured/i)).toBeInTheDocument();
  });

  it('credits the model when there was one', () => {
    state.digestData = { digest: 'Busy day.', generated_by: 'openai/gpt-oss-120b' };
    renderWithProviders(<BoardPage />);
    expect(screen.getByText(/Written by openai\/gpt-oss-120b/)).toBeInTheDocument();
  });

  it('switches between newest and top rated', async () => {
    renderWithProviders(<BoardPage />);
    const top = screen.getByRole('tab', { name: 'Top rated' });

    await userEvent.click(top);
    await waitFor(() => expect(top).toHaveAttribute('aria-selected', 'true'));
  });

  it('spells out the scoring weights', () => {
    renderWithProviders(<BoardPage />);
    expect(screen.getByText('Savage')).toBeInTheDocument();
    expect(screen.getByText('Cold take')).toBeInTheDocument();
    expect(screen.getByText('-2')).toBeInTheDocument();
  });
});
