import { describe, expect, it, vi, beforeEach } from 'vitest';
import userEvent from '@testing-library/user-event';

import { NewsPage } from './NewsPage';
import { renderWithProviders, screen } from '@/test/render';
import { LeagueNews, NewsArticle, TrendingPlayer } from '@/types';

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return { ...actual, useParams: () => ({ leagueId: '1' }) };
});

vi.mock('@/hooks/useLeagues', () => ({
  useLeague: () => ({ data: { id: 1, name: 'The Sunday Scaries Dynasty' } }),
}));

const state = vi.hoisted(() => ({
  news: undefined as LeagueNews | undefined,
  isLoading: false,
  trending: [] as TrendingPlayer[],
  digestMutate: vi.fn(),
  digestData: undefined as { digest: string; generated_by: string } | undefined,
}));

vi.mock('@/hooks/useNews', () => ({
  useLeagueNews: () => ({ data: state.news, isLoading: state.isLoading }),
  useTrending: () => ({ data: state.trending, isLoading: false }),
  useDigest: () => ({
    mutate: state.digestMutate,
    isLoading: false,
    data: state.digestData,
  }),
}));

const article = (over: Partial<NewsArticle> = {}): NewsArticle => ({
  id: '1',
  headline: 'Star RB limited in Friday practice',
  description: 'He sat out team periods.',
  byline: 'Wire Staff',
  published: '2026-09-12T20:00:00Z',
  image: null,
  url: null,
  athletes: ['Christian McCaffrey'],
  teams: ['San Francisco 49ers'],
  category: 'Injury',
  rostered_by: null,
  ...over,
});

beforeEach(() => {
  state.news = undefined;
  state.isLoading = false;
  state.trending = [];
  state.digestMutate = vi.fn();
  state.digestData = undefined;
});

describe('NewsPage', () => {
  it('says so when the wire has nothing', () => {
    state.news = { articles: [], rostered_count: 0, league_name: 'X' };
    renderWithProviders(<NewsPage />);
    expect(screen.getByText('The wire is quiet')).toBeInTheDocument();
  });

  it('separates your league from the rest of the NFL', () => {
    state.news = {
      articles: [
        article({ id: '1', rostered_by: 'Game of Throws' }),
        article({ id: '2', headline: 'Someone else entirely', rostered_by: null }),
      ],
      rostered_count: 1,
      league_name: 'X',
    };
    renderWithProviders(<NewsPage />);

    expect(screen.getByText("Your league's players")).toBeInTheDocument();
    expect(screen.getByText('Around the league')).toBeInTheDocument();
    expect(screen.getByText('Game of Throws')).toBeInTheDocument();
  });

  it('omits the league section when nothing touches it', () => {
    state.news = { articles: [article()], rostered_count: 0, league_name: 'X' };
    renderWithProviders(<NewsPage />);

    expect(screen.queryByText("Your league's players")).toBeNull();
    expect(screen.getByText('Around the league')).toBeInTheDocument();
  });

  it('counts how many stories touch the league', () => {
    state.news = {
      articles: [article({ rostered_by: 'Game of Throws' })],
      rostered_count: 1,
      league_name: 'X',
    };
    renderWithProviders(<NewsPage />);
    expect(screen.getByText('1 touch your league')).toBeInTheDocument();
  });

  it('summarizes on request', async () => {
    state.news = { articles: [], rostered_count: 0, league_name: 'X' };
    renderWithProviders(<NewsPage />);

    await userEvent.click(screen.getByRole('button', { name: /Summarize for my league/ }));
    expect(state.digestMutate).toHaveBeenCalled();
  });

  it('shows the digest when it comes back', () => {
    state.news = { articles: [], rostered_count: 0, league_name: 'X' };
    state.digestData = {
      digest: 'Game of Throws got a reality check.',
      generated_by: 'openai/gpt-oss-120b',
    };
    renderWithProviders(<NewsPage />);

    expect(screen.getByText('What changed for your league today')).toBeInTheDocument();
    expect(screen.getByText(/Game of Throws got a reality check\./)).toBeInTheDocument();
  });

  it('shows waiver buzz with the add counts', () => {
    state.news = { articles: [], rostered_count: 0, league_name: 'X' };
    state.trending = [
      { sleeper_id: '4034', name: 'Christian McCaffrey', position: 'RB', team: 'SF',
        count: 242829, headshot: null },
    ];
    renderWithProviders(<NewsPage />);

    expect(screen.getByText('Waiver buzz')).toBeInTheDocument();
    expect(screen.getByText('Christian McCaffrey')).toBeInTheDocument();
    // Formatted, because a bare 242829 is unreadable at a glance.
    expect(screen.getByText('242,829')).toBeInTheDocument();
  });

  it('hides waiver buzz entirely when there is none', () => {
    state.news = { articles: [], rostered_count: 0, league_name: 'X' };
    state.trending = [];
    renderWithProviders(<NewsPage />);
    expect(screen.queryByText('Waiver buzz')).toBeNull();
  });

  it('shows placeholders while the wire loads', () => {
    state.isLoading = true;
    const { container } = renderWithProviders(<NewsPage />);
    expect(container.querySelectorAll('.animate-pulse').length).toBeGreaterThan(0);
  });
});
