import React from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useTeam, useTeamRoster } from '@/hooks/useTeams';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { EmptyState } from '@/components/ui/EmptyState';
import { Skeleton } from '@/components/ui/Skeleton';
import { getPositionColor } from '@/utils';
import {
  ArrowLeftIcon,
  UserIcon,
  StarIcon,
  TrophyIcon,
  ChartBarIcon,
} from '@heroicons/react/24/outline';

export const TeamRosterPage: React.FC = () => {
  const { leagueId, teamId } = useParams<{ leagueId: string; teamId: string }>();
  const navigate = useNavigate();

  const {
    data: team,
    isLoading: teamLoading,
    error: teamError,
  } = useTeam(parseInt(teamId || '0', 10));

  const {
    data: roster,
    isLoading: rosterLoading,
    error: rosterError,
  } = useTeamRoster(parseInt(teamId || '0', 10));

  if (teamLoading || rosterLoading) {
    return (
      <div className="container mx-auto max-w-6xl px-4 py-8">
        <Skeleton className="mb-8 h-16 w-64" />
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="space-y-3 lg:col-span-2">
            <Skeleton className="h-40 w-full" />
            <Skeleton className="h-40 w-full" />
          </div>
          <Skeleton className="h-64 w-full" />
        </div>
      </div>
    );
  }

  if (teamError || rosterError || !team) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Card>
          <EmptyState
            icon={UserIcon}
            variant="error"
            title="Team Not Found"
            description="The team you're looking for doesn't exist or you don't have access to it."
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

  const getSlotColor = (slot: string) => {
    switch (slot) {
      case 'BENCH': return 'bg-surface-sunken text-fg-muted';
      case 'IR': return 'bg-error-100 text-error-600 dark:bg-error-900/40 dark:text-error-300';
      default: return 'bg-success-100 text-success-700 dark:bg-success-900/40 dark:text-success-300';
    }
  };

  const startingRoster = roster?.roster?.filter(player => player.lineup_slot_name !== 'BENCH' && player.lineup_slot_name !== 'IR') || [];
  const benchPlayers = roster?.roster?.filter(player => player.lineup_slot_name === 'BENCH') || [];
  const irPlayers = roster?.roster?.filter(player => player.lineup_slot_name === 'IR') || [];

  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center mb-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate(`/leagues/${leagueId}`)}
            className="mr-4"
          >
            <ArrowLeftIcon className="h-4 w-4 mr-1" />
            Back to League
          </Button>
        </div>
        
        <div className="flex items-center space-x-4">
          <div className="relative">
            <img
              src={team.logo_url}
              alt={`${team.name || team.abbreviation} logo`}
              className="w-16 h-16 rounded-full object-cover bg-surface-sunken"
              onError={(e) => {
                const target = e.target as HTMLImageElement;
                target.style.display = 'none';
              }}
            />
            <div className="absolute inset-0 w-16 h-16 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-bold text-xl">
              {team.abbreviation || team.name?.charAt(0) || '?'}
            </div>
          </div>

          <div>
            <h1 className="text-3xl font-bold text-fg mb-2">
              {team.name || `Team ${team.abbreviation}`}
            </h1>
            <div className="flex items-center space-x-4 text-sm text-fg-muted">
              <span className="flex items-center">
                <TrophyIcon className="h-4 w-4 mr-1" />
                <span className="tabular">{team.wins}-{team.losses}{team.ties > 0 && `-${team.ties}`}</span>
              </span>
              <span className="flex items-center">
                <ChartBarIcon className="h-4 w-4 mr-1" />
                <span className="tabular">{team.points_for.toFixed(1)}</span> PF
              </span>
              <span><span className="tabular">{team.points_against.toFixed(1)}</span> PA</span>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Starting Lineup */}
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <StarIcon className="h-5 w-5 mr-2" />
                Starting Lineup
                <span className="ml-2 text-sm font-normal text-fg-muted tabular">({startingRoster.length})</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {startingRoster.map((player, index) => (
                  <div key={index} className="flex items-center p-3 border border-border rounded-lg hover:bg-surface-sunken transition-colors">
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <div>
                          <h4 className="font-medium text-fg">{player.full_name}</h4>
                          <div className="flex items-center space-x-2 mt-1">
                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getPositionColor(player.position_name)}`}>
                              {player.position_name}
                            </span>
                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getSlotColor(player.lineup_slot_name)}`}>
                              {player.lineup_slot_name}
                            </span>
                          </div>
                        </div>
                        <div className="text-right">
                          {player.stats?.projected && (
                            <div className="text-sm text-fg-muted">
                              Proj: <span className="tabular">{(player.stats.projected['0'] || 0).toFixed(1)}</span>
                            </div>
                          )}
                          {player.stats?.actual && (
                            <div className="text-sm font-medium text-fg">
                              Actual: <span className="tabular">{(player.stats.actual['0'] || 0).toFixed(1)}</span>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
                {startingRoster.length === 0 && (
                  <p className="text-fg-muted text-center py-4">No starting lineup data available</p>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Bench Players */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <UserIcon className="h-5 w-5 mr-2" />
                Bench
                <span className="ml-2 text-sm font-normal text-fg-muted tabular">({benchPlayers.length})</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {benchPlayers.map((player, index) => (
                  <div key={index} className="flex items-center p-3 border border-border rounded-lg bg-surface-sunken">
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <div>
                          <h4 className="font-medium text-fg">{player.full_name}</h4>
                          <div className="flex items-center space-x-2 mt-1">
                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getPositionColor(player.position_name)}`}>
                              {player.position_name}
                            </span>
                          </div>
                        </div>
                        <div className="text-right">
                          {player.stats?.projected && (
                            <div className="text-sm text-fg-muted">
                              Proj: <span className="tabular">{(player.stats.projected['0'] || 0).toFixed(1)}</span>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
                {benchPlayers.length === 0 && (
                  <p className="text-fg-muted text-center py-4">No bench players</p>
                )}
              </div>
            </CardContent>
          </Card>

          {/* IR Players */}
          {irPlayers.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center text-error-600">
                  Injured Reserve
                  <span className="ml-2 text-sm font-normal text-fg-muted tabular">({irPlayers.length})</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {irPlayers.map((player, index) => (
                    <div key={index} className="flex items-center p-3 border border-error-200 rounded-lg bg-error-50 dark:border-error-900/40 dark:bg-error-900/20">
                      <div className="flex-1">
                        <div className="flex items-center justify-between">
                          <div>
                            <h4 className="font-medium text-error-900 dark:text-error-200">{player.full_name}</h4>
                            <div className="flex items-center space-x-2 mt-1">
                              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getPositionColor(player.position_name)}`}>
                                {player.position_name}
                              </span>
                              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-error-100 text-error-800 dark:bg-error-900/40 dark:text-error-300">
                                IR
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Sidebar - Team Stats */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Team Stats</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex justify-between">
                  <span className="text-fg-muted">Record:</span>
                  <span className="font-medium text-fg tabular">
                    {team.wins}-{team.losses}{team.ties > 0 && `-${team.ties}`}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-fg-muted">Points For:</span>
                  <span className="font-medium text-success-600 tabular">{team.points_for.toFixed(1)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-fg-muted">Points Against:</span>
                  <span className="font-medium text-error-600 tabular">{team.points_against.toFixed(1)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-fg-muted">Point Differential:</span>
                  <span className={`font-medium tabular ${
                    (team.points_for - team.points_against) > 0 ? 'text-success-600' : 'text-error-600'
                  }`}>
                    {(team.points_for - team.points_against > 0 ? '+' : '')}{(team.points_for - team.points_against).toFixed(1)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-fg-muted">PPG Average:</span>
                  <span className="font-medium text-fg tabular">
                    {((team.points_for) / (team.wins + team.losses + team.ties)).toFixed(1)}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Roster Summary</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-fg-muted">Starting:</span>
                  <span className="font-medium text-fg tabular">{startingRoster.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-fg-muted">Bench:</span>
                  <span className="font-medium text-fg tabular">{benchPlayers.length}</span>
                </div>
                {irPlayers.length > 0 && (
                  <div className="flex justify-between">
                    <span className="text-fg-muted">IR:</span>
                    <span className="font-medium text-error-600 tabular">{irPlayers.length}</span>
                  </div>
                )}
                <div className="flex justify-between pt-2 border-t border-border">
                  <span className="font-medium text-fg">Total:</span>
                  <span className="font-medium text-fg tabular">{roster?.roster?.length || 0}</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};