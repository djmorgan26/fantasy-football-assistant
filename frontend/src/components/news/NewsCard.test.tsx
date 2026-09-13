import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';

import { NewsCard } from './NewsCard';
import { NewsArticle } from '@/types';

const article = (over: Partial<NewsArticle> = {}): NewsArticle => ({
  id: '1',
  headline: 'Josh Allen (shoulder) listed as questionable',
  description: 'He was limited on Friday but is expected to play.',
  byline: 'Wire Staff',
  published: '2026-09-12T20:34:35Z',
  image: null,
  url: 'https://espn.example/story/1',
  athletes: ['Josh Allen'],
  teams: ['Buffalo Bills'],
  category: 'Injury',
  rostered_by: null,
  ...over,
});

describe('NewsCard', () => {
  it('leads with the headline and the category', () => {
    render(<NewsCard article={article()} />);
    expect(screen.getByText(/Josh Allen \(shoulder\)/)).toBeInTheDocument();
    expect(screen.getByText('Injury')).toBeInTheDocument();
  });

  it('names the fantasy team that rosters the player', () => {
    // This is the whole differentiator — a national site cannot say this.
    render(<NewsCard article={article({ rostered_by: 'Game of Throws' })} />);
    expect(screen.getByText('Game of Throws')).toBeInTheDocument();
  });

  it('stays quiet when nobody in the league rosters him', () => {
    render(<NewsCard article={article()} />);
    expect(screen.queryByText('Game of Throws')).toBeNull();
  });

  it('opens the source in a new tab, safely', () => {
    render(<NewsCard article={article()} />);
    const link = screen.getByRole('link', { name: /Read/ });
    expect(link).toHaveAttribute('href', 'https://espn.example/story/1');
    expect(link).toHaveAttribute('target', '_blank');
    expect(link).toHaveAttribute('rel', expect.stringContaining('noopener'));
  });

  it('omits the read link when the wire gave no url', () => {
    render(<NewsCard article={article({ url: null })} />);
    expect(screen.queryByRole('link', { name: /Read/ })).toBeNull();
  });

  it('renders without an image', () => {
    const { container } = render(<NewsCard article={article({ image: null })} />);
    expect(container.querySelector('img')).toBeNull();
  });

  it('shows the image when the wire supplied one', () => {
    const { container } = render(
      <NewsCard article={article({ image: 'https://img.example/a.jpg' })} />
    );
    expect(container.querySelector('img')).toHaveAttribute(
      'src',
      'https://img.example/a.jpg'
    );
  });

  it('falls back to a neutral tone for an unknown category', () => {
    render(<NewsCard article={article({ category: 'Something New' })} />);
    expect(screen.getByText('Something New')).toBeInTheDocument();
  });
});
