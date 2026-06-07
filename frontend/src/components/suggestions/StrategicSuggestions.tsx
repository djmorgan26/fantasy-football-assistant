import React, { useState, useEffect, useCallback } from 'react';
import { StrategicSuggestion, SuggestionFilters, League } from '@/types';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { EmptyState } from '@/components/ui/EmptyState';
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
  league: League;
  userTeamId?: number;
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
  league,
  userTeamId,
  className
}) => {
  const [filters, setFilters] = useState<SuggestionFilters>({});
  const [isLoading, setIsLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<StrategicSuggestion[]>([]);
  const [error, setError] = useState<string | null>(null);

  const fetchSuggestions = useCallback(async () => {
    if (!userTeamId) {
      setError('No team selected');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await api.get(`/suggestions/${league.id}/${userTeamId}`);
      setSuggestions(response.data);
    } catch (err: any) {
      console.error('Failed to fetch suggestions:', err);
      setError(err.detail || 'Failed to load AI suggestions. Please try again.');
      setSuggestions([]);
    } finally {
      setIsLoading(false);
    }
  }, [league.id, userTeamId]);

  useEffect(() => {
    fetchSuggestions();
  }, [fetchSuggestions]);

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
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <LightBulbIcon className="h-6 w-6 text-brand" />
            <CardTitle>Strategic Suggestions</CardTitle>
          </div>
          <Badge variant="secondary" size="sm">
            {filteredSuggestions.length} suggestions
          </Badge>
        </div>
        <p className="text-sm text-fg-muted">
          AI-powered recommendations to improve your team performance
        </p>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Filters */}
        <div className="flex flex-wrap gap-3">
          <div className="flex items-center space-x-2">
            <FunnelIcon className="h-4 w-4 text-fg-subtle" />
            <span className="text-sm font-medium text-fg">Filters:</span>
          </div>

          <select
            value={filters.type || 'all'}
            onChange={(e) => handleFilterChange('type', e.target.value)}
            className="px-3 py-1 border border-border rounded text-sm bg-surface-raised text-fg focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <option value="all">All Types</option>
            <option value="pickup">Pickup</option>
            <option value="drop">Drop</option>
            <option value="trade">Trade</option>
            <option value="lineup">Lineup</option>
          </select>

          <select
            value={filters.priority || 'all'}
            onChange={(e) => handleFilterChange('priority', e.target.value)}
            className="px-3 py-1 border border-border rounded text-sm bg-surface-raised text-fg focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <option value="all">All Priorities</option>
            <option value="high">High Priority</option>
            <option value="medium">Medium Priority</option>
            <option value="low">Low Priority</option>
          </select>
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
        ) : isLoading ? (
          <div className="flex justify-center py-8">
            <LoadingSpinner size="lg" />
          </div>
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
        {!error && (
          <div className="flex justify-center pt-4 border-t border-border">
            <Button
              variant="secondary"
              size="sm"
              onClick={fetchSuggestions}
              disabled={isLoading}
            >
              {isLoading ? 'Analyzing...' : 'Refresh Suggestions'}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
};