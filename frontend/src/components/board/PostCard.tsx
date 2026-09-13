import React, { useState } from 'react';
import {
  ChatBubbleLeftIcon,
  SparklesIcon,
  TrashIcon,
  AcademicCapIcon,
} from '@heroicons/react/24/outline';

import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { ReactionBar } from './ReactionBar';
import { BoardPost, ReactionKind } from '@/types';
import { cn, formatDate } from '@/utils';

const KIND_LABELS: Record<string, string> = {
  weekly_recap: 'Weekly Roast',
  power_rankings: 'Power Rankings',
  awards: 'Weekly Awards',
  season_recap: 'Season Recap',
  trash_talk: 'Trash Talk',
  digest: 'News Digest',
};

/** Above this the post is teaching the AI; the card says so. */
const TEACHING_THRESHOLD = 4;

interface PostCardProps {
  post: BoardPost;
  onReact: (postId: number, reaction: ReactionKind) => void;
  onComment: (postId: number, body: string) => void;
  onDelete?: (postId: number) => void;
  onToggleTraining?: (postId: number, allow: boolean) => void;
  busy?: boolean;
}

export const PostCard: React.FC<PostCardProps> = ({
  post,
  onReact,
  onComment,
  onDelete,
  onToggleTraining,
  busy,
}) => {
  const [showComments, setShowComments] = useState(false);
  const [draft, setDraft] = useState('');

  const teaching = post.allow_training && post.score >= TEACHING_THRESHOLD;

  const submitComment = (e: React.FormEvent) => {
    e.preventDefault();
    const body = draft.trim();
    if (!body) return;
    onComment(post.id, body);
    setDraft('');
    setShowComments(true);
  };

  return (
    <Card className={cn('transition-shadow', post.is_ai && 'border-l-4 border-l-accent')}>
      {/* Byline */}
      <div className="mb-3 flex flex-wrap items-center gap-x-2 gap-y-1">
        {post.is_ai ? (
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-accent/15">
            <SparklesIcon className="h-4 w-4 text-accent" />
          </span>
        ) : (
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-brand to-primary-700 text-xs font-bold text-brand-fg">
            {post.author_name.slice(0, 2).toUpperCase()}
          </span>
        )}

        <span className="font-semibold text-fg">{post.author_name}</span>

        {post.kind !== 'post' && (
          <Badge variant="secondary" size="sm">
            {KIND_LABELS[post.kind] ?? post.kind}
          </Badge>
        )}
        {post.week != null && (
          <span className="text-xs text-fg-subtle tabular">Week {post.week}</span>
        )}
        {post.created_at && (
          <span className="text-xs text-fg-subtle">{formatDate(post.created_at)}</span>
        )}

        <span className="ml-auto flex items-center gap-1">
          {post.score !== 0 && (
            <span
              className={cn(
                'font-display text-sm font-bold tabular',
                post.score > 0 ? 'text-brand' : 'text-fg-subtle'
              )}
              title="Weighted reactions plus comments"
            >
              {post.score > 0 ? `+${post.score}` : post.score}
            </span>
          )}
        </span>
      </div>

      {post.title && (
        <h3 className="mb-1.5 font-display text-base font-bold text-fg sm:text-lg">
          {post.title}
        </h3>
      )}

      <p className="whitespace-pre-wrap break-words text-[0.95rem] leading-relaxed text-fg">
        {post.body}
      </p>

      {/* The learning signal, stated plainly. People react more when they can
          see that reacting does something. */}
      {teaching && (
        <div className="mt-3 flex items-start gap-2 rounded-lg bg-brand/5 px-3 py-2 text-xs text-brand">
          <AcademicCapIcon className="mt-0.5 h-4 w-4 shrink-0" />
          <span>This one scored well enough that the AI is writing from it.</span>
        </div>
      )}

      <div className="mt-4 flex flex-col gap-3">
        <ReactionBar
          counts={post.reactions}
          mine={post.my_reactions}
          onReact={(reaction) => onReact(post.id, reaction)}
          disabled={busy}
        />

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => setShowComments((v) => !v)}
            className="inline-flex min-h-[2.25rem] items-center gap-1.5 rounded-lg px-2 text-sm font-semibold text-fg-muted transition-colors hover:bg-surface-sunken hover:text-fg focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <ChatBubbleLeftIcon className="h-4 w-4" />
            {post.comment_count === 0
              ? 'Reply'
              : `${post.comment_count} ${post.comment_count === 1 ? 'reply' : 'replies'}`}
          </button>

          {onToggleTraining && (
            <button
              type="button"
              onClick={() => onToggleTraining(post.id, !post.allow_training)}
              className="ml-auto text-xs text-fg-subtle underline-offset-2 hover:text-fg-muted hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              {post.allow_training ? 'Keep out of AI training' : 'Allow in AI training'}
            </button>
          )}

          {onDelete && post.is_mine && (
            <button
              type="button"
              onClick={() => onDelete(post.id)}
              aria-label="Delete post"
              className="rounded-lg p-1.5 text-fg-subtle transition-colors hover:bg-error-50 hover:text-error-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring dark:hover:bg-error-900/20"
            >
              <TrashIcon className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>

      {showComments && (
        <div className="mt-4 border-t border-border pt-4">
          <div className="flex flex-col gap-3">
            {post.comments.map((comment) => (
              <div key={comment.id} className="flex gap-2.5">
                <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-surface-sunken text-[10px] font-bold text-fg-muted">
                  {comment.author_name.slice(0, 2).toUpperCase()}
                </span>
                <div className="min-w-0">
                  <div className="flex flex-wrap items-baseline gap-x-2">
                    <span className="text-sm font-semibold text-fg">{comment.author_name}</span>
                    {comment.created_at && (
                      <span className="text-xs text-fg-subtle">
                        {formatDate(comment.created_at)}
                      </span>
                    )}
                  </div>
                  <p className="whitespace-pre-wrap break-words text-sm text-fg-muted">
                    {comment.body}
                  </p>
                </div>
              </div>
            ))}

            <form onSubmit={submitComment} className="flex gap-2">
              <input
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                placeholder="Say something"
                aria-label="Write a reply"
                className="min-h-[2.75rem] w-full rounded-lg border border-border bg-surface-raised px-3 py-2 text-fg placeholder:text-fg-subtle focus:border-brand focus:outline-none focus-visible:ring-2 focus-visible:ring-ring/40 sm:min-h-[2.5rem] sm:text-sm"
              />
              <Button type="submit" size="sm" disabled={!draft.trim() || busy}>
                Post reply
              </Button>
            </form>
          </div>
        </div>
      )}
    </Card>
  );
};
