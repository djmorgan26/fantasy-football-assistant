import React, { useState, useEffect, useCallback } from 'react';
import { StrategicSuggestion, SuggestionFilters } from '@/types';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { SkeletonList } from '@/components/ui/Skeleton';
import { EmptyState } from '@/components/ui/EmptyState';
import { Select } from '@/components/ui/Select';
import {
  LightBulbIcon,
  FunnelIcon,
  TrophyIcon,
  ArrowTrendingUpIcon,
  UserGroupIcon,
  SwatchIcon,
  ExclamationTriangleIcon
} from '@heroicons/react/24/outline';
import { cn } from '@/utils';
import api from '@/services/api';

interface StrategicSuggestionsProps {
  leagueId: number;
  userTeamId?: number;
  /**
   * Whether the caller is still working out which team is mine. Without this
   * an absent `userTeamId` is ambiguous — it means either "still loading" or
   * "you have not claimed a team", and this used to assume the second and
   * flash a red error on every visit.
   */
  resolvingTeam?: boolean;
  className?: string;
}

const SuggestionCard: React.FC<{ suggestion: StrategicSuggestion }> = ({ suggestion }) => {
  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
        return 'error';
      case 'medium':
        return 'warning';
      case 'low':
        return 'success';
      default:
        return 'default';
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'pickup':
        return <ArrowTrendingUpIcon className="h-4 w-4" />;
      case 'drop':
        return <SwatchIcon className="h-4 w-4" />;
      case 'trade':
        return <UserGroupIcon className="h-4 w-4" />;
      case 'lineup':
        return <TrophyIcon className="h-4 w-4" />;
      default:
        return <LightBulbIcon className="h-4 w-4" />;
    }
  };

  return (
    <Card className="hover:shadow-elevation-3 transition-shadow duration-200">
      <CardContent className="p-4">
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center space-x-2 text-fg-muted">
            {getTypeIcon(suggestion.type)}
            <Badge variant={getPriorityColor(suggestion.priority)} size="sm">
              {suggestion.priority.toUpperCase()}
            </Badge>
            <Badge variant="secondary" size="sm">
              {suggestion.type.toUpperCase()}
            </Badge>
          </div>
          <div className="text-right">
            <div className="text-sm text-fg-muted">Confidence</div>
            <div className="font-bold text-brand tabular">
              {Math.round(suggestion.confidence_score * 100)}%
            </div>
          </div>
        </div>

        <h3 className="font-semibold text-lg mb-2 text-fg">{suggestion.title}</h3>
        <p className="text-fg-muted mb-3">{suggestion.description}</p>

        <div className="space-y-2">
          <div>
            <span className="text-sm font-medium text-fg">Reasoning:</span>
            <p className="text-sm text-fg-muted">{suggestion.reasoning}</p>
          </div>

          <div>
            <span className="text-sm font-medium text-fg">Potential Impact:</span>
            <p className="text-sm text-fg-muted">{suggestion.potential_impact}</p>
          </div>

          {suggestion.action_details && (
            <div className="mt-3 p-3 bg-surface-sunken rounded-lg">
              <div className="text-sm font-medium text-fg mb-2">Action Details:</div>
              <div className="space-y-1 text-sm text-fg-muted">
                {suggestion.action_details.player_name && (
                  <div>Target: <span className="font-medium text-fg">{suggestion.action_details.player_name}</span></div>
                )}
                {suggestion.action_details.suggested_bid && (
                  <div>Suggested Bid: <span className="font-medium text-fg tabular">${suggestion.action_details.suggested_bid}</span></div>
                )}
                {suggestion.action_details.lineup_changes && (
                  <div>
                    <div className="font-medium text-fg">Lineup Changes:</div>
                    {Object.entries(suggestion.action_details.lineup_changes).map(([position, change]) => (
                      <div key={position} className="ml-2">
                        {position}: {change}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {suggestion.context?.budget_remaining && (
            <div className="text-xs text-fg-subtle tabular">
              Budget Remaining: ${suggestion.context.budget_remaining}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

export const StrategicSuggestions: React.FC<StrategicSuggestionsProps> = ({
  leagueId,
  userTeamId,
  resolvingTeam = false,
  className
}) => {
  const [filters, setFilters] = useState<SuggestionFilters>({});
  const [isLoading, setIsLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<StrategicSuggestion[]>([]);
  const [error, setError] = useState<string | null>(null);

  const fetchSuggestions = useCallback(async () => {
    // Nothing to ask about yet. Whether that is because the lookup is still in
    // flight or because there is no team to ask about is the caller's to say.
    if (!userTeamId) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await api.get(`/suggestions/${leagueId}/${userTeamId}`);
      setSuggestions(response.data);
    } catch (err: any) {
      console.error('Failed to fetch suggestions:', err);
      setError(err.detail || 'Failed to load AI suggestions. Please try again.');
      setSuggestions([]);
    } finally {
      setIsLoading(false);
    }
  }, [leagueId, userTeamId]);

  useEffect(() => {
    fetchSuggestions();
  }, [fetchSuggestions]);

  // Waiting on the team lookup reads as loading, not as an error and not as
  // an empty list of suggestions.
  const pending = isLoading || resolvingTeam || (!userTeamId && !error);

  const filteredSuggestions = suggestions.filter(suggestion => {
    if (filters.type && suggestion.type !== filters.type) return false;
    if (filters.priority && suggestion.priority !== filters.priority) return false;
    return true;
  });

  const handleFilterChange = (key: keyof SuggestionFilters, value: string) => {
    setFilters(prev => ({
      ...prev,
      [key]: value === 'all' ? undefined : value
    }));
  };

  return (
    <Card className={cn('', className)}>
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div className="flex min-w-0 items-center space-x-2">
            <LightBulbIcon className="h-6 w-6 shrink-0 text-brand" />
            <CardTitle>Strategic Suggestions</CardTitle>
          </div>
          <Badge variant="secondary" size="sm" className="shrink-0 whitespace-nowrap">
            {filteredSuggestions.length}
          </Badge>
        </div>
        <p className="text-sm text-fg-muted">
          AI-powered recommendations to improve your team performance
        </p>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="hidden items-center space-x-2 sm:flex">
            <FunnelIcon className="h-4 w-4 text-fg-subtle" />
            <span className="text-sm font-medium text-fg">Filters:</span>
          </div>

          <Select
            value={filters.type || 'all'}
            onChange={(value) => handleFilterChange('type', value)}
            options={[
              { value: 'all', label: 'All Types' },
              { value: 'pickup', label: 'Pickup' },
              { value: 'drop', label: 'Drop' },
              { value: 'trade', label: 'Trade' },
              { value: 'lineup', label: 'Lineup' },
            ]}
            size="sm"
            className="w-32 flex-1 sm:flex-none"
          />

          <Select
            value={filters.priority || 'all'}
            onChange={(value) => handleFilterChange('priority', value)}
            options={[
              { value: 'all', label: 'All Priorities' },
              { value: 'high', label: 'High Priority' },
              { value: 'medium', label: 'Medium Priority' },
              { value: 'low', label: 'Low Priority' },
            ]}
            size="sm"
            className="w-40 flex-1 sm:flex-none"
          />
        </div>

        {/* Suggestions List */}
        {error ? (
          <EmptyState
            icon={ExclamationTriangleIcon}
            variant="error"
            title="Unable to Load Suggestions"
            description={error}
            action={
              <Button variant="secondary" size="sm" onClick={fetchSuggestions}>
                Try Again
              </Button>
            }
          />
        ) : !resolvingTeam && !userTeamId ? (
          <EmptyState
            icon={LightBulbIcon}
            title="Claim your team first"
            description="These are recommendations for your roster, so we need to know which one it is."
          />
        ) : pending ? (
          <SkeletonList rows={3} height="h-28" />
        ) : filteredSuggestions.length > 0 ? (
          <div className="space-y-4">
            {filteredSuggestions.map((suggestion) => (
              <SuggestionCard key={suggestion.id} suggestion={suggestion} />
            ))}
          </div>
        ) : suggestions.length === 0 ? (
          <EmptyState
            icon={LightBulbIcon}
            title="No suggestions available"
            description="Check back later for AI-powered recommendations."
          />
        ) : (
          <EmptyState
            icon={LightBulbIcon}
            title="No suggestions match your filters"
            description="Try adjusting your filters to see more recommendations."
          />
        )}

        {/* Refresh Button */}
        {!error && userTeamId && (
          <div className="flex justify-center pt-4 border-t border-border">
            <Button
              variant="secondary"
              size="sm"
              onClick={fetchSuggestions}
              disabled={pending || !userTeamId}
            >
              {pending ? 'Analyzing...' : 'Refresh Suggestions'}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
};