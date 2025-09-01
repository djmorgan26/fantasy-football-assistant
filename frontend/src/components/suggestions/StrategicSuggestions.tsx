import React, { useState } from 'react';
import { StrategicSuggestion, SuggestionFilters, League } from '@/types';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { 
  LightBulbIcon,
  FunnelIcon,
  TrophyIcon,
  ArrowTrendingUpIcon,
  UserGroupIcon,
  SwatchIcon
} from '@heroicons/react/24/outline';
import { cn } from '@/utils';

interface StrategicSuggestionsProps {
  league: League;
  userTeamId?: number;
  className?: string;
}

// Mock data for demonstration - in a real app this would come from an AI service
const generateMockSuggestions = (league: League, userTeamId?: number): StrategicSuggestion[] => {
  return [
    {
      id: '1',
      type: 'pickup',
      priority: 'high',
      title: 'Target Handcuff Running Back',
      description: 'Consider picking up backup RB for injury protection',
      reasoning: 'Your starting RB has a history of minor injuries and the backup is available for free',
      potential_impact: 'Could save your season if your starter gets injured',
      confidence_score: 0.85,
      action_details: {
        player_name: 'Available Backup RB',
        suggested_bid: 15,
      },
      context: {
        budget_remaining: 85,
      }
    },
    {
      id: '2',
      type: 'trade',
      priority: 'medium',
      title: 'Upgrade WR Position',
      description: 'Trade for a more consistent WR2',
      reasoning: 'Your current WR2 is underperforming and you have RB depth to spare',
      potential_impact: 'Could increase weekly scoring by 3-5 points',
      confidence_score: 0.72,
      action_details: {
        trade_targets: [12, 34],
      }
    },
    {
      id: '3',
      type: 'lineup',
      priority: 'high',
      title: 'Optimize This Week\'s Lineup',
      description: 'Start your flex player over current WR2',
      reasoning: 'Better matchup against weaker defense this week',
      potential_impact: 'Projected 4-6 point improvement',
      confidence_score: 0.91,
      action_details: {
        lineup_changes: {
          'WR2': 'Move to bench',
          'FLEX': 'Move to WR2'
        }
      }
    },
    {
      id: '4',
      type: 'drop',
      priority: 'low',
      title: 'Drop Underperforming Player',
      description: 'Consider dropping bench player for lottery ticket',
      reasoning: 'Current bench player has limited upside, better options available',
      potential_impact: 'Frees up roster spot for better prospect',
      confidence_score: 0.65,
    }
  ];
};

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
    <Card className="hover:shadow-md transition-shadow duration-200">
      <CardContent className="p-4">
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center space-x-2">
            {getTypeIcon(suggestion.type)}
            <Badge variant={getPriorityColor(suggestion.priority)} size="sm">
              {suggestion.priority.toUpperCase()}
            </Badge>
            <Badge variant="secondary" size="sm">
              {suggestion.type.toUpperCase()}
            </Badge>
          </div>
          <div className="text-right">
            <div className="text-sm text-gray-600">Confidence</div>
            <div className="font-bold text-primary-600">
              {Math.round(suggestion.confidence_score * 100)}%
            </div>
          </div>
        </div>

        <h3 className="font-semibold text-lg mb-2">{suggestion.title}</h3>
        <p className="text-gray-600 mb-3">{suggestion.description}</p>
        
        <div className="space-y-2">
          <div>
            <span className="text-sm font-medium text-gray-700">Reasoning:</span>
            <p className="text-sm text-gray-600">{suggestion.reasoning}</p>
          </div>
          
          <div>
            <span className="text-sm font-medium text-gray-700">Potential Impact:</span>
            <p className="text-sm text-gray-600">{suggestion.potential_impact}</p>
          </div>

          {suggestion.action_details && (
            <div className="mt-3 p-3 bg-gray-50 rounded-lg">
              <div className="text-sm font-medium text-gray-700 mb-2">Action Details:</div>
              <div className="space-y-1 text-sm">
                {suggestion.action_details.player_name && (
                  <div>Target: <span className="font-medium">{suggestion.action_details.player_name}</span></div>
                )}
                {suggestion.action_details.suggested_bid && (
                  <div>Suggested Bid: <span className="font-medium">${suggestion.action_details.suggested_bid}</span></div>
                )}
                {suggestion.action_details.lineup_changes && (
                  <div>
                    <div className="font-medium">Lineup Changes:</div>
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
            <div className="text-xs text-gray-500">
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
  
  // In a real app, this would be fetched from an API
  const suggestions = generateMockSuggestions(league, userTeamId);
  
  const filteredSuggestions = suggestions.filter(suggestion => {
    if (filters.type && suggestion.type !== filters.type) return false;
    if (filters.priority && suggestion.priority !== filters.priority) return false;
    return true;
  });

  const handleFilterChange = (key: keyof SuggestionFilters, value: any) => {
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
            <LightBulbIcon className="h-6 w-6 text-primary-600" />
            <CardTitle>Strategic Suggestions</CardTitle>
          </div>
          <Badge variant="secondary" size="sm">
            {filteredSuggestions.length} suggestions
          </Badge>
        </div>
        <p className="text-sm text-gray-600">
          AI-powered recommendations to improve your team performance
        </p>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Filters */}
        <div className="flex flex-wrap gap-3">
          <div className="flex items-center space-x-2">
            <FunnelIcon className="h-4 w-4 text-gray-400" />
            <span className="text-sm font-medium text-gray-700">Filters:</span>
          </div>
          
          <select
            value={filters.type || 'all'}
            onChange={(e) => handleFilterChange('type', e.target.value)}
            className="px-3 py-1 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
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
            className="px-3 py-1 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="all">All Priorities</option>
            <option value="high">High Priority</option>
            <option value="medium">Medium Priority</option>
            <option value="low">Low Priority</option>
          </select>
        </div>

        {/* Suggestions List */}
        {isLoading ? (
          <div className="flex justify-center py-8">
            <LoadingSpinner size="lg" />
          </div>
        ) : filteredSuggestions.length > 0 ? (
          <div className="space-y-4">
            {filteredSuggestions.map((suggestion) => (
              <SuggestionCard key={suggestion.id} suggestion={suggestion} />
            ))}
          </div>
        ) : (
          <div className="text-center py-8">
            <LightBulbIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              No suggestions found
            </h3>
            <p className="text-gray-600">
              Try adjusting your filters or check back later for new recommendations.
            </p>
          </div>
        )}

        {/* Refresh Button */}
        <div className="flex justify-center pt-4 border-t border-gray-200">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              setIsLoading(true);
              // Simulate API call
              setTimeout(() => setIsLoading(false), 1500);
            }}
            disabled={isLoading}
          >
            {isLoading ? 'Analyzing...' : 'Refresh Suggestions'}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};