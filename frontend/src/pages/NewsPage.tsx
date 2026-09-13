import React from 'react';
import { useParams } from 'react-router-dom';
import { NewspaperIcon, SparklesIcon } from '@heroicons/react/24/outline';

import { PageContainer, PageHeader } from '@/components/layout/Page';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { EmptyState } from '@/components/ui/EmptyState';
import { Skeleton } from '@/components/ui/Skeleton';
import { ToolHeader } from '@/components/ui/ToolHeader';
import { NewsCard } from '@/components/news/NewsCard';
import { WaiverBuzz } from '@/components/news/WaiverBuzz';
import { useLeague } from '@/hooks/useLeagues';
import { useDigest, useLeagueNews } from '@/hooks/useNews';

export const NewsPage: React.FC = () => {
  const { leagueId } = useParams<{ leagueId: string }>();
  const id = parseInt(leagueId || '0', 10);

  const { data: league } = useLeague(id);
  const { data: news, isLoading } = useLeagueNews(id);
  const digest = useDigest(id);

  const rostered = news?.articles.filter((a) => a.rostered_by) ?? [];
  const rest = news?.articles.filter((a) => !a.rostered_by) ?? [];

  return (
    <PageContainer>
      <PageHeader
        backTo={`/leagues/${id}`}
        backLabel="Back to League"
        title="News"
        subtitle={`The NFL wire, filtered to the players ${league?.name ?? 'your league'} actually rosters`}
      />

      <ToolHeader
        icon={NewspaperIcon}
        title="League Wire"
        context={news ? `${news.rostered_count} touch your league` : undefined}
        subtitle="Anything involving a rostered player is flagged with the team that owns him."
        actions={
          <Button
            size="sm"
            variant="secondary"
            loading={digest.isLoading}
            onClick={() => digest.mutate()}
          >
            <SparklesIcon className="h-4 w-4" />
            Summarize for my league
          </Button>
        }
      />

      {digest.data && (
        <Card className="mt-4 border-l-4 border-l-accent">
          <h2 className="mb-2 font-display text-base font-bold text-fg">
            What changed for your league today
          </h2>
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
        <div className="space-y-6 lg:col-span-2">
          {isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-28 w-full rounded-card" />
              ))}
            </div>
          ) : !news || news.articles.length === 0 ? (
            <Card>
              <EmptyState
                icon={NewspaperIcon}
                title="The wire is quiet"
                description="No NFL news came back just now. It refreshes every few minutes."
              />
            </Card>
          ) : (
            <>
              {rostered.length > 0 && (
                <section>
                  <h2 className="mb-3 font-display text-lg font-bold text-fg">
                    Your league's players
                  </h2>
                  <div className="space-y-3">
                    {rostered.map((article) => (
                      <NewsCard key={article.id} article={article} />
                    ))}
                  </div>
                </section>
              )}

              {rest.length > 0 && (
                <section>
                  <h2 className="mb-3 font-display text-lg font-bold text-fg">
                    Around the league
                  </h2>
                  <div className="space-y-3">
                    {rest.map((article) => (
                      <NewsCard key={article.id} article={article} />
                    ))}
                  </div>
                </section>
              )}
            </>
          )}
        </div>

        <div className="space-y-6">
          <WaiverBuzz />
        </div>
      </div>
    </PageContainer>
  );
};
