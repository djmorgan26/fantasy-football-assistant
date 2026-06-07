import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import {
  NewspaperIcon,
  FireIcon,
  ArrowPathIcon,
  ExclamationTriangleIcon
} from '@heroicons/react/24/outline';
import api from '@/services/api';
import toast from 'react-hot-toast';

interface WeeklyRecapProps {
  leagueId: number;
  leagueName: string;
  currentWeek: number;
  className?: string;
}

export const WeeklyRecap: React.FC<WeeklyRecapProps> = ({
  leagueId,
  leagueName,
  currentWeek,
  className
}) => {
  const [recap, setRecap] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedWeek, setSelectedWeek] = useState(currentWeek > 1 ? currentWeek - 1 : 1);

  const fetchRecap = useCallback(async (week: number) => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await api.get(`/recap/league/${leagueId}/week/${week}`);
      setRecap(response.data.recap);
    } catch (err: any) {
      console.error('Failed to fetch weekly recap:', err);
      const errorMsg = err.detail || 'Failed to load weekly recap. The AI might be taking a nap.';
      setError(errorMsg);
      toast.error(errorMsg);
    } finally {
      setIsLoading(false);
    }
  }, [leagueId]);

  useEffect(() => {
    if (leagueId && selectedWeek) {
      fetchRecap(selectedWeek);
    }
  }, [leagueId, selectedWeek, fetchRecap]);

  const handleWeekChange = (newWeek: number) => {
    if (newWeek >= 1 && newWeek <= currentWeek) {
      setSelectedWeek(newWeek);
    }
  };

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-gradient-to-br from-brand to-accent rounded-lg">
              <FireIcon className="h-6 w-6 text-brand-fg" />
            </div>
            <div>
              <CardTitle className="flex items-center space-x-2">
                <NewspaperIcon className="h-5 w-5 text-fg-muted" />
                <span>Weekly Roast Report</span>
              </CardTitle>
              <p className="text-sm text-fg-muted">
                AI-powered brutality for {leagueName}
              </p>
            </div>
          </div>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => fetchRecap(selectedWeek)}
            disabled={isLoading}
          >
            <ArrowPathIcon className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </CardHeader>

      <CardContent>
        {/* Week Selector */}
        <div className="flex items-center justify-center space-x-2 mb-6">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => handleWeekChange(selectedWeek - 1)}
            disabled={selectedWeek <= 1 || isLoading}
          >
            ← Previous
          </Button>
          <div className="px-4 py-2 bg-surface-sunken rounded-lg font-semibold text-fg tabular">
            Week {selectedWeek}
          </div>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => handleWeekChange(selectedWeek + 1)}
            disabled={selectedWeek >= currentWeek || isLoading}
          >
            Next →
          </Button>
        </div>

        {/* Recap Content */}
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-12">
            <LoadingSpinner size="lg" />
            <p className="text-fg-muted mt-4 animate-pulse">
              AI is crafting the perfect roast...
            </p>
          </div>
        ) : error ? (
          <div className="text-center py-8">
            <ExclamationTriangleIcon className="h-12 w-12 text-warning-500 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-fg mb-2">
              Recap Unavailable
            </h3>
            <p className="text-fg-muted mb-4">{error}</p>
            <Button variant="secondary" size="sm" onClick={() => fetchRecap(selectedWeek)}>
              Try Again
            </Button>
          </div>
        ) : recap ? (
          <div className="prose prose-sm max-w-none">
            <div className="bg-surface-sunken rounded-lg p-6 border border-border shadow-inner">
              <div className="text-fg leading-relaxed whitespace-pre-wrap">
                {recap}
              </div>
            </div>

            {/* Fun footer */}
            <div className="mt-4 text-center">
              <p className="text-xs text-fg-subtle italic">
                🔥 AI-generated roasts • Feelings may be hurt • No refunds on emotional damage
              </p>
            </div>
          </div>
        ) : (
          <div className="text-center py-8 text-fg-muted">
            <NewspaperIcon className="h-12 w-12 text-fg-subtle mx-auto mb-4" />
            <p>No recap available for this week</p>
          </div>
        )}

        {/* Share button (future enhancement) */}
        {recap && !isLoading && !error && (
          <div className="mt-6 flex justify-center">
            <Button
              variant="primary"
              size="sm"
              onClick={() => {
                navigator.clipboard.writeText(recap);
                toast.success('Recap copied to clipboard! Share the pain!');
              }}
            >
              📋 Copy to Clipboard
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
