import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useLeague } from '@/hooks/useLeagues';
import { useLeagueTeams, useTeamRoster } from '@/hooks/useTeams';
import { useCurrentUser } from '@/hooks/useAuth';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
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

  const getStatusBadge = (status: string, injuryStatus?: string) => {
    switch (status) {
      case 'active':
        return <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded-full">Healthy</span>;
      case 'questionable':
        return <span className="px-2 py-1 bg-yellow-100 text-yellow-800 text-xs rounded-full">Q - {injuryStatus}</span>;
      case 'injured':
        return <span className="px-2 py-1 bg-red-100 text-red-800 text-xs rounded-full">Injured</span>;
      case 'bye':
        return <span className="px-2 py-1 bg-gray-100 text-gray-800 text-xs rounded-full">Bye Week</span>;
      default:
        return null;
    }
  };

  const getPositionColor = (position: string) => {
    switch (position) {
      case 'QB': return 'text-purple-600 bg-purple-100';
      case 'RB': return 'text-green-600 bg-green-100';
      case 'WR': return 'text-blue-600 bg-blue-100';
      case 'TE': return 'text-orange-600 bg-orange-100';
      case 'K': return 'text-pink-600 bg-pink-100';
      case 'D/ST': return 'text-gray-600 bg-gray-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const getLineupSlotColor = (slot: string) => {
    return slot === 'BENCH' ? 'text-gray-500 bg-gray-100' : 'text-blue-600 bg-blue-100';
  };

  if (!userTeam) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-6xl">
        <Card>
          <CardContent className="text-center py-12">
            <ExclamationTriangleIcon className="h-12 w-12 text-yellow-500 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              No Team Selected
            </h3>
            <p className="text-gray-600 mb-4">
              Please select your team first to view your roster.
            </p>
            <Link to={`/leagues/${leagueId}`}>
              <Button>Back to League</Button>
            </Link>
          </CardContent>
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
            className="flex items-center text-gray-600 hover:text-gray-900"
          >
            <ArrowLeftIcon className="h-4 w-4 mr-1" />
            Back to League
          </Link>
        </div>
        
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <TrophyIcon className="h-8 w-8 text-blue-600 mr-3" />
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                My Roster
              </h1>
              <p className="text-gray-600">
                {userTeam.name} • {league?.name}
              </p>
            </div>
          </div>
          
          <div className="flex items-center space-x-4">
            <select
              value={selectedWeek}
              onChange={(e) => setSelectedWeek(parseInt(e.target.value))}
              className="p-2 border rounded-lg"
            >
              {Array.from({length: 17}, (_, i) => i + 1).map(week => (
                <option key={week} value={week}>
                  Week {week}
                </option>
              ))}
            </select>
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
                <div className="text-center p-4 bg-blue-50 rounded-lg">
                  <div className="text-2xl font-bold text-blue-600">{userTeam.wins}-{userTeam.losses}</div>
                  <div className="text-sm text-blue-800">Record</div>
                </div>
                <div className="text-center p-4 bg-green-50 rounded-lg">
                  <div className="text-2xl font-bold text-green-600">{userTeam.points_for.toFixed(1)}</div>
                  <div className="text-sm text-green-800">Points For</div>
                </div>
                <div className="text-center p-4 bg-purple-50 rounded-lg">
                  <div className="text-2xl font-bold text-purple-600">{totalPoints.toFixed(1)}</div>
                  <div className="text-sm text-purple-800">Season Points</div>
                </div>
                <div className="text-center p-4 bg-orange-50 rounded-lg">
                  <div className="text-2xl font-bold text-orange-600">{projectedPoints.toFixed(1)}</div>
                  <div className="text-sm text-orange-800">Week {selectedWeek} Proj</div>
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
                    key={player.id}
                    className="p-4 border rounded-lg hover:shadow-md transition-shadow"
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
                            <h4 className="font-semibold text-gray-900">{player.full_name}</h4>
                            <span className={`px-2 py-1 text-xs font-medium rounded-full ${getPositionColor(player.position_name)}`}>
                              {player.position_name}
                            </span>
                            <span className={`px-2 py-1 text-xs font-medium rounded-full ${getLineupSlotColor(player.lineup_slot_name)}`}>
                              {player.lineup_slot_name}
                            </span>
                          </div>
                          
                          <div className="flex items-center space-x-3 text-sm text-gray-600">
                            <span>{player.pro_team_id}</span>
                            <span className="flex items-center">
                              <TrophyIcon className="h-3 w-3 mr-1" />
                              {(player.stats?.actual?.['0'] || 0).toFixed(1)}
                            </span>
                            <span className="flex items-center">
                              <FireIcon className="h-3 w-3 mr-1" />
                              {(player.stats?.projected?.['0'] || 0).toFixed(1)}
                            </span>
                          </div>
                        </div>
                      </div>
                      
                      <div className="flex items-center space-x-2">
                        <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded-full">Active</span>
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
                    key={player.id}
                    className="p-3 border rounded-lg hover:shadow-md transition-shadow bg-gray-50"
                  >
                    <div className="flex items-center space-x-3">
                      {/* Player Avatar */}
                      <div className="w-8 h-8 bg-gradient-to-br from-gray-400 to-gray-600 rounded-full flex items-center justify-center text-white font-bold text-xs">
                        {player.full_name.split(' ').map(n => n[0]).join('').slice(0, 2)}
                      </div>
                      
                      {/* Player Info */}
                      <div className="flex-1">
                        <div className="flex items-center space-x-2 mb-1">
                          <h5 className="font-medium text-gray-900 text-sm">{player.full_name}</h5>
                          <span className={`px-1.5 py-0.5 text-xs font-medium rounded-full ${getPositionColor(player.position_name)}`}>
                            {player.position_name}
                          </span>
                        </div>
                        
                        <div className="flex items-center space-x-2 text-xs text-gray-600">
                          <span>{player.pro_team_id}</span>
                          <span>{(player.stats?.actual?.['0'] || 0).toFixed(1)} pts</span>
                        </div>
                      </div>
                    </div>
                    </div>
                  ))}
                </div>
              )}
              
              {!rosterLoading && (
                <div className="mt-4 pt-3 border-t">
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