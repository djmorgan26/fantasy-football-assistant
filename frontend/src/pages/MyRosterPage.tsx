import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useLeague } from '@/hooks/useLeagues';
import { useLeagueTeams, useTeamRoster } from '@/hooks/useTeams';
import { useCurrentUser } from '@/hooks/useAuth';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Select } from '@/components/ui/Select';
import { EmptyState } from '@/components/ui/EmptyState';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { getPositionColor } from '@/utils';
import {
  ArrowLeftIcon,
  TrophyIcon,
  UserIcon,
  FireIcon,
  ChartBarIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';


export const MyRosterPage: React.FC = () => {
  const { leagueId } = useParams<{ leagueId: string }>();
  const { data: league } = useLeague(parseInt(leagueId || '0', 10));
  const { data: teams } = useLeagueTeams(parseInt(leagueId || '0', 10));
  const { data: currentUser } = useCurrentUser();
  
  const [selectedWeek, setSelectedWeek] = useState(league?.current_week || 1);

  const userTeam = teams?.find(team => team.owner_user_id === currentUser?.id);
  
  // Fetch roster data for the user's team
  const { data: rosterData, isLoading: rosterLoading } = useTeamRoster(
    userTeam?.id || 0, 
    selectedWeek
  );

  // Process roster data
  const rosterPlayers = rosterData?.roster || [];
  
  const starterPlayers = rosterPlayers.filter(player => 
    player.lineup_slot_name !== 'Bench'
  );
  const benchPlayers = rosterPlayers.filter(player => 
    player.lineup_slot_name === 'Bench'
  );
  
  const totalPoints = rosterPlayers.reduce((sum, player) => {
    const stats = player.stats?.actual || {};
    return sum + (stats['0'] || 0);
  }, 0);
  
  const projectedPoints = rosterPlayers.reduce((sum, player) => {
    const stats = player.stats?.projected || {};
    return sum + (stats['0'] || 0);
  }, 0);

  const getLineupSlotColor = (slot: string) => {
    return slot === 'BENCH'
      ? 'text-fg-muted bg-surface-sunken'
      : 'text-brand bg-brand/10';
  };

  if (!userTeam) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-6xl">
        <Card>
          <EmptyState
            icon={ExclamationTriangleIcon}
            title="No Team Selected"
            description="Please select your team first to view your roster."
            action={
              <Link to={`/leagues/${leagueId}`}>
                <Button>Back to League</Button>
              </Link>
            }
          />
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center mb-4">
          <Link
            to={`/leagues/${leagueId}`}
            className="flex items-center text-fg-muted hover:text-fg transition-colors"
          >
            <ArrowLeftIcon className="h-4 w-4 mr-1" />
            Back to League
          </Link>
        </div>

        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <TrophyIcon className="h-8 w-8 text-brand mr-3" />
            <div>
              <h1 className="text-3xl font-bold text-fg">
                My Roster
              </h1>
              <p className="text-fg-muted">
                {userTeam.name} • {league?.name}
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-4">
            <Select
              value={String(selectedWeek)}
              onChange={(v) => setSelectedWeek(parseInt(v, 10))}
              options={Array.from({ length: 17 }, (_, i) => ({
                value: String(i + 1),
                label: `Week ${i + 1}`,
              }))}
            />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Roster Stats */}
        <div className="lg:col-span-3">
          <Card className="mb-6">
            <CardHeader>
              <CardTitle>Team Stats</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="text-center p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                  <div className="font-display text-2xl font-bold text-blue-600 dark:text-blue-400 tabular">{userTeam.wins}-{userTeam.losses}</div>
                  <div className="text-sm text-blue-800 dark:text-blue-300">Record</div>
                </div>
                <div className="text-center p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
                  <div className="font-display text-2xl font-bold text-green-600 dark:text-green-400 tabular">{userTeam.points_for.toFixed(1)}</div>
                  <div className="text-sm text-green-800 dark:text-green-300">Points For</div>
                </div>
                <div className="text-center p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
                  <div className="font-display text-2xl font-bold text-purple-600 dark:text-purple-400 tabular">{totalPoints.toFixed(1)}</div>
                  <div className="text-sm text-purple-800 dark:text-purple-300">Season Points</div>
                </div>
                <div className="text-center p-4 bg-orange-50 dark:bg-orange-900/20 rounded-lg">
                  <div className="font-display text-2xl font-bold text-orange-600 dark:text-orange-400 tabular">{projectedPoints.toFixed(1)}</div>
                  <div className="text-sm text-orange-800 dark:text-orange-300">Week {selectedWeek} Proj</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Starting Lineup */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <UserIcon className="h-5 w-5 mr-2" />
                Starting Lineup
              </CardTitle>
            </CardHeader>
            <CardContent>
              {rosterLoading ? (
                <div className="flex justify-center py-8">
                  <LoadingSpinner size="sm" />
                </div>
              ) : (
                <div className="space-y-3">
                  {starterPlayers.map((player) => (
                  <div
                    key={player.player_id}
                    className="p-4 border border-border rounded-lg hover:shadow-elevation-3 transition-shadow"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        {/* Player Avatar */}
                        <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white font-bold text-sm">
                          {player.full_name.split(' ').map(n => n[0]).join('').slice(0, 2)}
                        </div>

                        {/* Player Info */}
                        <div>
                          <div className="flex items-center space-x-2 mb-1">
                            <h4 className="font-semibold text-fg">{player.full_name}</h4>
                            <span className={`px-2 py-1 text-xs font-medium rounded-full ${getPositionColor(player.position_name)}`}>
                              {player.position_name}
                            </span>
                            <span className={`px-2 py-1 text-xs font-medium rounded-full ${getLineupSlotColor(player.lineup_slot_name)}`}>
                              {player.lineup_slot_name}
                            </span>
                          </div>

                          <div className="flex items-center space-x-3 text-sm text-fg-muted">
                            <span>{player.pro_team_id}</span>
                            <span className="flex items-center">
                              <TrophyIcon className="h-3 w-3 mr-1" />
                              <span className="tabular">{(player.stats?.actual?.['0'] || 0).toFixed(1)}</span>
                            </span>
                            <span className="flex items-center">
                              <FireIcon className="h-3 w-3 mr-1" />
                              <span className="tabular">{(player.stats?.projected?.['0'] || 0).toFixed(1)}</span>
                            </span>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center space-x-2">
                        <Badge variant="success" size="sm">Active</Badge>
                      </div>
                    </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Bench */}
        <div>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <ChartBarIcon className="h-5 w-5 mr-2" />
                Bench
              </CardTitle>
            </CardHeader>
            <CardContent>
              {rosterLoading ? (
                <div className="flex justify-center py-8">
                  <LoadingSpinner size="sm" />
                </div>
              ) : (
                <div className="space-y-3">
                  {benchPlayers.map((player) => (
                  <div
                    key={player.player_id}
                    className="p-3 border border-border rounded-lg hover:shadow-elevation-3 transition-shadow bg-surface-sunken"
                  >
                    <div className="flex items-center space-x-3">
                      {/* Player Avatar */}
                      <div className="w-8 h-8 bg-gradient-to-br from-gray-400 to-gray-600 rounded-full flex items-center justify-center text-white font-bold text-xs">
                        {player.full_name.split(' ').map(n => n[0]).join('').slice(0, 2)}
                      </div>

                      {/* Player Info */}
                      <div className="flex-1">
                        <div className="flex items-center space-x-2 mb-1">
                          <h5 className="font-medium text-fg text-sm">{player.full_name}</h5>
                          <span className={`px-1.5 py-0.5 text-xs font-medium rounded-full ${getPositionColor(player.position_name)}`}>
                            {player.position_name}
                          </span>
                        </div>

                        <div className="flex items-center space-x-2 text-xs text-fg-muted">
                          <span>{player.pro_team_id}</span>
                          <span className="tabular">{(player.stats?.actual?.['0'] || 0).toFixed(1)} pts</span>
                        </div>
                      </div>
                    </div>
                    </div>
                  ))}
                </div>
              )}
              
              {!rosterLoading && (
                <div className="mt-4 pt-3 border-t border-border">
                  <Button fullWidth variant="secondary" size="sm">
                    Manage Lineup
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};