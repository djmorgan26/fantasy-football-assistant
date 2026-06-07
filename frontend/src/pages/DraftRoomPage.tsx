import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useLeague } from '@/hooks/useLeagues';
import { Button } from '@/components/ui/Button';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { Tabs } from '@/components/ui/Tabs';
import { ValueBoard } from '@/components/draft/ValueBoard';
import { LiveAssistant } from '@/components/draft/LiveAssistant';
import {
  ArrowLeftIcon,
  TableCellsIcon,
  BoltIcon,
} from '@heroicons/react/24/outline';

type Tab = 'board' | 'live';

export const DraftRoomPage: React.FC = () => {
  const { leagueId } = useParams<{ leagueId: string }>();
  const navigate = useNavigate();
  const id = parseInt(leagueId || '0', 10);
  const { data: league, isLoading } = useLeague(id);
  const [tab, setTab] = useState<Tab>('board');

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <LoadingSpinner size="lg" className="mt-12" />
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      <Button
        variant="ghost"
        size="sm"
        onClick={() => navigate(`/leagues/${id}`)}
        className="mb-4"
      >
        <ArrowLeftIcon className="h-4 w-4 mr-1" />
        Back to League
      </Button>

      <div className="mb-6">
        <h1 className="text-3xl font-bold text-fg">Draft Room</h1>
        <p className="text-fg-muted mt-1">
          {league?.name} · rankings tuned to your league's scoring
        </p>
      </div>

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
    </div>
  );
};
