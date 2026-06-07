import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useLeagues } from '@/hooks/useLeagues';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { EmptyState } from '@/components/ui/EmptyState';
import { SkeletonCard } from '@/components/ui/Skeleton';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import {
  PlusIcon,
  TrophyIcon,
  UsersIcon,
  FireIcon,
  ChartBarIcon,
  CogIcon,
} from '@heroicons/react/24/outline';
import { formatDate } from '@/utils';
import { leaguesService } from '@/services/leagues';
import toast from 'react-hot-toast';

export const LeaguesPage: React.FC = () => {
  const { data: leagues, isLoading, error, refetch } = useLeagues();
  const [syncingLeagues, setSyncingLeagues] = useState<Set<number>>(new Set());
  

  const handleSyncLeague = async (e: React.MouseEvent, leagueId: number) => {
    e.preventDefault();
    e.stopPropagation();
    setSyncingLeagues(prev => new Set([...prev, leagueId]));
    
    try {
      const response = await leaguesService.syncLeague(leagueId);
      
      if (response.success) {
        toast.success('League data synced successfully!');
        refetch(); // Refresh the leagues list to show updated data
      } else {
        toast.error(response.message || 'Failed to sync league data');
      }
    } catch (error) {
      console.error('Sync error:', error);
      toast.error('Failed to sync league data');
    } finally {
      setSyncingLeagues(prev => {
        const newSet = new Set(prev);
        newSet.delete(leagueId);
        return newSet;
      });
    }
  };

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-6xl">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-6xl">
        <Card>
          <EmptyState
            icon={TrophyIcon}
            variant="error"
            title="Couldn't load your leagues"
            description={error.detail}
            action={<Button onClick={() => refetch()}>Try Again</Button>}
          />
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      {/* Header */}
      <div className="mb-8">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-display-sm text-fg mb-2">Your Leagues</h1>
            <p className="text-fg-muted">
              Manage your fantasy football leagues across ESPN and Sleeper
            </p>
          </div>
          <div className="mt-4 sm:mt-0 flex space-x-3">
            <Link to="/leagues/connect">
              <Button variant="secondary" size="sm">
                <PlusIcon className="h-5 w-5 mr-2" />
                ESPN League
              </Button>
            </Link>
            <Link to="/leagues/sleeper/connect">
              <Button variant="primary" size="sm">
                <PlusIcon className="h-5 w-5 mr-2" />
                Sleeper League
              </Button>
            </Link>
          </div>
        </div>
      </div>

      {/* Leagues Grid */}
      {!leagues || leagues.length === 0 ? (
        <Card>
          <EmptyState
            icon={TrophyIcon}
            title="No leagues connected yet"
            description="Connect your ESPN fantasy league to get started with intelligent analysis, trade recommendations, and roster insights."
            action={
              <Link to="/leagues/connect">
                <Button size="lg">
                  <PlusIcon className="h-5 w-5 mr-2" />
                  Connect Your First League
                </Button>
              </Link>
            }
          />
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {leagues.map((league) => (
            <Card key={league.id} className="transition-shadow hover:shadow-elevation-3">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="text-lg leading-tight mb-2">
                      {league.name}
                    </CardTitle>
                    <div className="flex items-center space-x-3 text-sm text-fg-muted">
                      <span className="flex items-center">
                        <UsersIcon className="h-4 w-4 mr-1" />
                        {league.size}
                      </span>
                      <span className="flex items-center">
                        <FireIcon className="h-4 w-4 mr-1" />
                        Week {league.current_week}
                      </span>
                    </div>
                  </div>
                  <div className="text-right">
                    <Badge variant="secondary" size="sm" className="tabular">
                      {league.season_year}
                    </Badge>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {/* League Stats */}
                  <div className="grid grid-cols-2 gap-3">
                    <div className="text-center p-3 bg-surface-sunken rounded-lg">
                      <div className="text-sm font-medium text-fg capitalize">
                        {league.scoring_type}
                      </div>
                      <div className="text-xs text-fg-muted">Scoring</div>
                    </div>
                    <div className="text-center p-3 bg-surface-sunken rounded-lg">
                      <div className="text-sm font-medium text-fg">
                        {league.is_public ? 'Public' : 'Private'}
                      </div>
                      <div className="text-xs text-fg-muted">League</div>
                    </div>
                  </div>

                  {/* League Info */}
                  <div className="text-xs text-fg-subtle space-y-1">
                    <div className="flex justify-between">
                      <span>ESPN ID:</span>
                      <span className="font-mono tabular">{league.espn_league_id}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Connected:</span>
                      <span>{formatDate(league.created_at)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Last Sync:</span>
                      <span>
                        {league.last_synced ? formatDate(league.last_synced) : 'Never'}
                      </span>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex space-x-2 pt-2">
                    <Link to={`/leagues/${league.id}`} className="flex-1">
                      <Button size="sm" fullWidth>
                        View League
                      </Button>
                    </Link>
                    <Button
                      size="sm"
                      variant="secondary"
                      title="Sync League Data"
                      aria-label="Sync league data"
                      onClick={(e) => handleSyncLeague(e, league.id)}
                      disabled={syncingLeagues.has(league.id)}
                    >
                      {syncingLeagues.has(league.id) ? (
                        <LoadingSpinner size="sm" />
                      ) : (
                        <CogIcon className="h-4 w-4" />
                      )}
                    </Button>
                  </div>

                  {/* Quick Actions */}
                  <div className="flex space-x-1 pt-1">
                    <Link to={`/leagues/${league.id}/trades`} className="flex-1">
                      <Button size="sm" variant="ghost" fullWidth className="text-xs">
                        <ChartBarIcon className="h-3 w-3 mr-1" />
                        Trades
                      </Button>
                    </Link>
                    <Link to={`/leagues/${league.id}/roster`} className="flex-1">
                      <Button size="sm" variant="ghost" fullWidth className="text-xs">
                        <TrophyIcon className="h-3 w-3 mr-1" />
                        Roster
                      </Button>
                    </Link>
                    <Link to={`/leagues/${league.id}/players`} className="flex-1">
                      <Button size="sm" variant="ghost" fullWidth className="text-xs">
                        <UsersIcon className="h-3 w-3 mr-1" />
                        Players
                      </Button>
                    </Link>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}

          {/* Add League Card */}
          <Link to="/leagues/connect">
            <Card className="h-full border-2 border-dashed border-border transition-shadow hover:border-fg-subtle hover:shadow-elevation-3">
              <CardContent className="text-center py-12">
                <PlusIcon className="h-12 w-12 text-fg-subtle mx-auto mb-4" />
                <h3 className="font-display text-lg font-bold text-fg mb-2">
                  Connect New League
                </h3>
                <p className="text-fg-muted text-sm">
                  Add another ESPN fantasy league to analyze
                </p>
              </CardContent>
            </Card>
          </Link>
        </div>
      )}
    </div>
  );
};