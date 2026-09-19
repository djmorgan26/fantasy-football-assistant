import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import {
  AcademicCapIcon,
  ChatBubbleLeftRightIcon,
  NewspaperIcon,
} from '@heroicons/react/24/outline';

import { PageContainer, PageHeader } from '@/components/layout/Page';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { EmptyState } from '@/components/ui/EmptyState';
import { SkeletonCard, SkeletonList } from '@/components/ui/Skeleton';
import { Tabs } from '@/components/ui/Tabs';
import { ToolHeader } from '@/components/ui/ToolHeader';
import { PostCard } from '@/components/board/PostCard';
import { REACTIONS } from '@/components/board/ReactionBar';
import { useLeague } from '@/hooks/useLeagues';
import {
  useBoardPosts,
  useBoardStats,
  useComment,
  useCreatePost,
  useDeletePost,
  useReact,
  useSetTraining,
  useVoiceSamples,
} from '@/hooks/useBoard';
import { useDigest } from '@/hooks/useNews';

export const BoardPage: React.FC = () => {
  const { leagueId } = useParams<{ leagueId: string }>();
  const id = parseInt(leagueId || '0', 10);

  const { data: league } = useLeague(id);
  const [sort, setSort] = useState<'new' | 'top'>('new');
  const [draft, setDraft] = useState('');

  const { data: posts, isLoading } = useBoardPosts(id, sort);
  const { data: stats } = useBoardStats(id);
  const { data: samples, isLoading: samplesLoading } = useVoiceSamples(id);

  const createPost = useCreatePost(id);
  const react = useReact(id);
  const comment = useComment(id);
  const deletePost = useDeletePost(id);
  const setTraining = useSetTraining(id);
  const digest = useDigest(id);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const body = draft.trim();
    if (!body) return;
    createPost.mutate({ body }, { onSuccess: () => setDraft('') });
  };

  return (
    <PageContainer>
      <PageHeader
        backTo={`/leagues/${id}`}
        backLabel="Back to League"
        title="The Board"
        subtitle={`${league?.name ?? 'Your league'} · post it, rate it, and the AI learns how you talk`}
      />

      <ToolHeader
        icon={ChatBubbleLeftRightIcon}
        title="League Board"
        context={stats ? `${stats.posts} posts` : undefined}
        subtitle="Everything posted here is private to this league."
        actions={
          <Button
            size="sm"
            variant="secondary"
            loading={digest.isLoading}
            onClick={() => digest.mutate({ publish: true })}
          >
            <NewspaperIcon className="h-4 w-4" />
            Post today's digest
          </Button>
        }
      />

      {digest.data && (
        <Card className="mt-4 border-l-4 border-l-accent">
          <p className="whitespace-pre-wrap break-words text-[0.95rem] leading-relaxed text-fg">
            {digest.data.digest}
          </p>
          <p className="mt-2 text-xs text-fg-subtle">
            {digest.data.generated_by === 'fallback'
              ? 'Facts only — no AI writer configured.'
              : `Written by ${digest.data.generated_by}`}
          </p>
        </Card>
      )}

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          {/* Composer */}
          <Card className="mb-5">
            <form onSubmit={submit}>
              <label htmlFor="board-composer" className="sr-only">
                Write a post
              </label>
              <textarea
                id="board-composer"
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                rows={3}
                placeholder="What happened this week?"
                className="w-full resize-y rounded-lg border border-border bg-surface-raised px-3 py-2.5 text-fg placeholder:text-fg-subtle focus:border-brand focus:outline-none focus-visible:ring-2 focus-visible:ring-ring/40 sm:text-sm"
              />
              <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
                <p className="text-xs text-fg-subtle">
                  Posts the league rates highly teach the AI your voice.
                </p>
                <Button
                  type="submit"
                  size="sm"
                  disabled={!draft.trim()}
                  loading={createPost.isLoading}
                >
                  Post
                </Button>
              </div>
            </form>
          </Card>

          <Tabs
            className="mb-4"
            aria-label="Sort posts"
            value={sort}
            onChange={(key) => setSort(key as 'new' | 'top')}
            tabs={[
              { key: 'new', label: 'Newest' },
              { key: 'top', label: 'Top rated' },
            ]}
          />

          {isLoading ? (
            <div className="space-y-4">
              <SkeletonCard />
              <SkeletonCard />
            </div>
          ) : !posts || posts.length === 0 ? (
            <Card>
              <EmptyState
                icon={ChatBubbleLeftRightIcon}
                title="Nothing on the board yet"
                description="Post the first thing. Generated recaps land here too, and everything the league rates highly becomes material the AI writes from."
              />
            </Card>
          ) : (
            <div className="space-y-4">
              {posts.map((post) => (
                <PostCard
                  key={post.id}
                  post={post}
                  busy={react.isLoading || comment.isLoading}
                  onReact={(postId, reaction) => react.mutate({ postId, reaction })}
                  onComment={(postId, body) => comment.mutate({ postId, body })}
                  onDelete={(postId) => deletePost.mutate(postId)}
                  onToggleTraining={(postId, allow) => setTraining.mutate({ postId, allow })}
                />
              ))}
            </div>
          )}
        </div>

        {/* What the AI has learned so far. Showing this is what makes people
            bother reacting: the cause and the effect sit on one screen. */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AcademicCapIcon className="h-5 w-5 text-brand" />
                What the AI learned
              </CardTitle>
            </CardHeader>
            <CardContent>
              {/* "Nothing yet" is a claim about the league, so it waits until
                  we know it is true rather than being the default view. */}
              {samplesLoading ? (
                <SkeletonList rows={3} height="h-20" />
              ) : !samples || samples.length === 0 ? (
                <p className="text-sm text-fg-muted">
                  Nothing yet. Once a post clears{' '}
                  <span className="font-semibold text-fg tabular">+4</span>, it becomes one of
                  the examples the writer copies the voice of.
                </p>
              ) : (
                <div className="space-y-3">
                  {samples.slice(0, 5).map((sample) => (
                    <div key={sample.id} className="rounded-lg bg-surface-sunken p-3">
                      <div className="mb-1 flex items-center justify-between gap-2">
                        <span className="truncate text-xs font-semibold text-fg">
                          {sample.author_name}
                        </span>
                        <span className="shrink-0 font-display text-sm font-bold text-brand tabular">
                          +{sample.score}
                        </span>
                      </div>
                      <p className="line-clamp-3 text-xs text-fg-muted">{sample.text}</p>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>How scoring works</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2">
                {REACTIONS.map((reaction) => (
                  <li
                    key={reaction.kind}
                    className="flex items-center justify-between gap-3 text-sm"
                  >
                    <span className="flex items-center gap-2 text-fg-muted">
                      <span aria-hidden className="text-base">
                        {reaction.glyph}
                      </span>
                      {reaction.label}
                    </span>
                    <span
                      className={`font-semibold tabular ${
                        reaction.weight > 0 ? 'text-brand' : 'text-fg-subtle'
                      }`}
                    >
                      {reaction.weight > 0 ? `+${reaction.weight}` : reaction.weight}
                    </span>
                  </li>
                ))}
                <li className="flex items-center justify-between gap-3 border-t border-border pt-2 text-sm">
                  <span className="text-fg-muted">A reply</span>
                  <span className="font-semibold text-brand tabular">+2</span>
                </li>
              </ul>
              <p className="mt-3 text-xs text-fg-subtle">
                Replies count most: bothering to answer is the strongest sign a post landed.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </PageContainer>
  );
};
