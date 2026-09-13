import { describe, expect, it, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { PostCard } from './PostCard';
import { BoardPost } from '@/types';

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

const noop = () => undefined;

describe('PostCard', () => {
  it('offers all five typed reactions, not a like/dislike binary', () => {
    render(<PostCard post={post()} onReact={noop} onComment={noop} />);

    ['Savage', 'Funny', 'Brutal', 'Actually smart', 'Cold take'].forEach((label) => {
      expect(screen.getByRole('button', { name: `React: ${label}` })).toBeInTheDocument();
    });
  });

  it('reports the reaction that was tapped', async () => {
    const onReact = vi.fn();
    render(<PostCard post={post()} onReact={onReact} onComment={noop} />);

    await userEvent.click(screen.getByRole('button', { name: 'React: Savage' }));
    expect(onReact).toHaveBeenCalledWith(1, 'savage');
  });

  it('marks your own reactions as pressed so a second tap reads as undo', () => {
    render(
      <PostCard
        post={post({ my_reactions: ['funny'], reactions: { savage: 0, funny: 2, brutal: 0, smart: 0, cold: 0 } })}
        onReact={noop}
        onComment={noop}
      />
    );

    const mine = screen.getByRole('button', { name: 'Remove Funny reaction' });
    expect(mine).toHaveAttribute('aria-pressed', 'true');
    expect(within(mine).getByText('2')).toBeInTheDocument();
  });

  it('says when a post is scoring well enough to teach the AI', () => {
    render(<PostCard post={post({ score: 6 })} onReact={noop} onComment={noop} />);
    expect(screen.getByText(/the AI is writing from it/i)).toBeInTheDocument();
  });

  it('stays quiet about training when the score is below the threshold', () => {
    render(<PostCard post={post({ score: 3 })} onReact={noop} onComment={noop} />);
    expect(screen.queryByText(/the AI is writing from it/i)).toBeNull();
  });

  it('never claims to be teaching a post that opted out', () => {
    render(
      <PostCard post={post({ score: 10, allow_training: false })} onReact={noop} onComment={noop} />
    );
    expect(screen.queryByText(/the AI is writing from it/i)).toBeNull();
  });

  it('credits the assistant for its own posts and labels the kind', () => {
    render(
      <PostCard
        post={post({ is_ai: true, author_name: 'The Commissioner', kind: 'weekly_recap' })}
        onReact={noop}
        onComment={noop}
      />
    );

    expect(screen.getByText('The Commissioner')).toBeInTheDocument();
    expect(screen.getByText('Weekly Roast')).toBeInTheDocument();
  });

  it('submits a reply and clears the box', async () => {
    const onComment = vi.fn();
    render(<PostCard post={post()} onReact={noop} onComment={onComment} />);

    await userEvent.click(screen.getByRole('button', { name: /reply/i }));

    const box = screen.getByLabelText('Write a reply');
    await userEvent.type(box, 'Filing a counter-complaint.');
    await userEvent.click(screen.getByRole('button', { name: 'Post reply' }));

    expect(onComment).toHaveBeenCalledWith(1, 'Filing a counter-complaint.');
    expect(box).toHaveValue('');
  });

  it('will not send an empty reply', async () => {
    const onComment = vi.fn();
    render(<PostCard post={post()} onReact={noop} onComment={onComment} />);

    await userEvent.click(screen.getByRole('button', { name: /reply/i }));
    expect(screen.getByRole('button', { name: 'Post reply' })).toBeDisabled();
    expect(onComment).not.toHaveBeenCalled();
  });

  it('only offers delete on your own posts', () => {
    const { rerender } = render(
      <PostCard post={post({ is_mine: true })} onReact={noop} onComment={noop} onDelete={noop} />
    );
    expect(screen.getByRole('button', { name: 'Delete post' })).toBeInTheDocument();

    rerender(
      <PostCard post={post({ is_mine: false })} onReact={noop} onComment={noop} onDelete={noop} />
    );
    expect(screen.queryByRole('button', { name: 'Delete post' })).toBeNull();
  });
});
