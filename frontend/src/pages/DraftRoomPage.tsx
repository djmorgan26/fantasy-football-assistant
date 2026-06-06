import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useLeague } from '@/hooks/useLeagues';
import { Button } from '@/components/ui/Button';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { ValueBoard } from '@/components/draft/ValueBoard';
import { LiveAssistant } from '@/components/draft/LiveAssistant';
import { cn } from '@/utils';
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
        <h1 className="text-3xl font-bold text-gray-900">Draft Room</h1>
        <p className="text-gray-600 mt-1">
          {league?.name} · rankings tuned to your league's scoring
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6 border-b border-gray-200">
        <TabButton
          active={tab === 'board'}
          onClick={() => setTab('board')}
          icon={<TableCellsIcon className="h-5 w-5" />}
          label="Big Board"
        />
        <TabButton
          active={tab === 'live'}
          onClick={() => setTab('live')}
          icon={<BoltIcon className="h-5 w-5" />}
          label="Live Draft"
        />
      </div>

      {tab === 'board' ? <ValueBoard leagueId={id} /> : <LiveAssistant leagueId={id} />}
    </div>
  );
};

const TabButton: React.FC<{
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
}> = ({ active, onClick, icon, label }) => (
  <button
    onClick={onClick}
    className={cn(
      'flex items-center gap-2 px-4 py-2.5 font-medium text-sm border-b-2 -mb-px transition-colors',
      active
        ? 'border-primary-600 text-primary-600'
        : 'border-transparent text-gray-500 hover:text-gray-700'
    )}
  >
    {icon}
    {label}
  </button>
);
