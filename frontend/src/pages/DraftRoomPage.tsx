import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useLeague } from '@/hooks/useLeagues';
import { Skeleton, SkeletonList } from '@/components/ui/Skeleton';
import { Tabs } from '@/components/ui/Tabs';
import { ValueBoard } from '@/components/draft/ValueBoard';
import { LiveAssistant } from '@/components/draft/LiveAssistant';
import { TableCellsIcon, BoltIcon } from '@heroicons/react/24/outline';
import { PageContainer, PageHeader } from '@/components/layout/Page';

type Tab = 'board' | 'live';

export const DraftRoomPage: React.FC = () => {
  const { leagueId } = useParams<{ leagueId: string }>();
  const id = parseInt(leagueId || '0', 10);
  const { data: league, isLoading } = useLeague(id);
  const [tab, setTab] = useState<Tab>('board');

  if (isLoading) {
    return (
      <PageContainer>
        <div className="mb-6 space-y-3">
          <Skeleton className="h-9 w-1/2" />
          <Skeleton className="h-4 w-2/3" />
        </div>
        <Skeleton className="mb-4 h-10 w-64 rounded-lg" />
        <SkeletonList rows={6} height="h-14" />
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <PageHeader
        backTo={`/leagues/${id}`}
        backLabel="Back to League"
        title="Draft Room"
        subtitle={`${league?.name ?? ''} · rankings tuned to your league's scoring`}
      />

      {/* Tabs */}
      <Tabs
        className="mb-6"
        aria-label="Draft views"
        value={tab}
        onChange={(key) => setTab(key as Tab)}
        tabs={[
          { key: 'board', label: 'Big Board', icon: TableCellsIcon },
          { key: 'live', label: 'Live Draft', icon: BoltIcon },
        ]}
      />

      {tab === 'board' ? <ValueBoard leagueId={id} /> : <LiveAssistant leagueId={id} />}
    </PageContainer>
  );
};
