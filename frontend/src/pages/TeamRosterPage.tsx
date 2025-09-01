import React from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useTeam, useTeamRoster } from '@/hooks/useTeams';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
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
      <div className="container mx-auto px-4 py-8">
        <LoadingSpinner size="lg" className="mt-12" />
      </div>
    );
  }

  if (teamError || rosterError || !team) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Card>
          <CardContent>
            <div className="text-center py-12">
              <h3 className="text-lg font-medium text-gray-900 mb-2">Team Not Found</h3>
              <p className="text-gray-600 mb-4">
                The team you're looking for doesn't exist or you don't have access to it.
              </p>
              <Link to={`/leagues/${leagueId}`}>
                <Button>Back to League</Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  const getPositionColor = (position: string) => {
    switch (position) {
      case 'QB': return 'bg-purple-100 text-purple-800';
      case 'RB': return 'bg-green-100 text-green-800';
      case 'WR': return 'bg-blue-100 text-blue-800';
      case 'TE': return 'bg-orange-100 text-orange-800';
      case 'K': return 'bg-yellow-100 text-yellow-800';
      case 'D/ST': return 'bg-gray-100 text-gray-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getSlotColor = (slot: string) => {
    switch (slot) {
      case 'BENCH': return 'bg-gray-100 text-gray-600';
      case 'IR': return 'bg-red-100 text-red-600';
      default: return 'bg-green-100 text-green-700';
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
              className="w-16 h-16 rounded-full object-cover bg-gray-100"
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
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              {team.name || `Team ${team.abbreviation}`}
            </h1>
            <div className="flex items-center space-x-4 text-sm text-gray-600">
              <span className="flex items-center">
                <TrophyIcon className="h-4 w-4 mr-1" />
                {team.wins}-{team.losses}{team.ties > 0 && `-${team.ties}`}
              </span>
              <span className="flex items-center">
                <ChartBarIcon className="h-4 w-4 mr-1" />
                {team.points_for.toFixed(1)} PF
              </span>
              <span>{team.points_against.toFixed(1)} PA</span>
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
                <span className="ml-2 text-sm font-normal text-gray-500">({startingRoster.length})</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {startingRoster.map((player, index) => (
                  <div key={index} className="flex items-center p-3 border rounded-lg hover:bg-gray-50">
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <div>
                          <h4 className="font-medium text-gray-900">{player.full_name}</h4>
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
                            <div className="text-sm text-gray-600">
                              Proj: {(player.stats.projected['0'] || 0).toFixed(1)}
                            </div>
                          )}
                          {player.stats?.actual && (
                            <div className="text-sm font-medium text-gray-900">
                              Actual: {(player.stats.actual['0'] || 0).toFixed(1)}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
                {startingRoster.length === 0 && (
                  <p className="text-gray-500 text-center py-4">No starting lineup data available</p>
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
                <span className="ml-2 text-sm font-normal text-gray-500">({benchPlayers.length})</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {benchPlayers.map((player, index) => (
                  <div key={index} className="flex items-center p-3 border rounded-lg bg-gray-50">
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <div>
                          <h4 className="font-medium text-gray-700">{player.full_name}</h4>
                          <div className="flex items-center space-x-2 mt-1">
                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getPositionColor(player.position_name)}`}>
                              {player.position_name}
                            </span>
                          </div>
                        </div>
                        <div className="text-right">
                          {player.stats?.projected && (
                            <div className="text-sm text-gray-500">
                              Proj: {(player.stats.projected['0'] || 0).toFixed(1)}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
                {benchPlayers.length === 0 && (
                  <p className="text-gray-500 text-center py-4">No bench players</p>
                )}
              </div>
            </CardContent>
          </Card>

          {/* IR Players */}
          {irPlayers.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center text-red-600">
                  Injured Reserve
                  <span className="ml-2 text-sm font-normal text-gray-500">({irPlayers.length})</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {irPlayers.map((player, index) => (
                    <div key={index} className="flex items-center p-3 border border-red-200 rounded-lg bg-red-50">
                      <div className="flex-1">
                        <div className="flex items-center justify-between">
                          <div>
                            <h4 className="font-medium text-red-900">{player.full_name}</h4>
                            <div className="flex items-center space-x-2 mt-1">
                              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getPositionColor(player.position_name)}`}>
                                {player.position_name}
                              </span>
                              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
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
                  <span className="text-gray-600">Record:</span>
                  <span className="font-medium">
                    {team.wins}-{team.losses}{team.ties > 0 && `-${team.ties}`}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Points For:</span>
                  <span className="font-medium text-green-600">{team.points_for.toFixed(1)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Points Against:</span>
                  <span className="font-medium text-red-600">{team.points_against.toFixed(1)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Point Differential:</span>
                  <span className={`font-medium ${
                    (team.points_for - team.points_against) > 0 ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {(team.points_for - team.points_against > 0 ? '+' : '')}{(team.points_for - team.points_against).toFixed(1)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">PPG Average:</span>
                  <span className="font-medium">
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
                  <span className="text-gray-600">Starting:</span>
                  <span className="font-medium">{startingRoster.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Bench:</span>
                  <span className="font-medium">{benchPlayers.length}</span>
                </div>
                {irPlayers.length > 0 && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">IR:</span>
                    <span className="font-medium text-red-600">{irPlayers.length}</span>
                  </div>
                )}
                <div className="flex justify-between pt-2 border-t">
                  <span className="font-medium text-gray-900">Total:</span>
                  <span className="font-medium">{roster?.roster?.length || 0}</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};