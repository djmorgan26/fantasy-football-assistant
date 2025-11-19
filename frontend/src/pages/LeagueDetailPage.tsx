import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useLeague, useDisconnectLeague, useSyncLeague } from '@/hooks/useLeagues';
import { useLeagueTeams } from '@/hooks/useTeams';
import { useMatchups } from '@/hooks/useMatchups';
import { useWaiverBudgets } from '@/hooks/useWaiverBudgets';
import { useCurrentUser } from '@/hooks/useAuth';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { MatchupCard } from '@/components/matchups/MatchupCard';
import { WaiverBudgetCard } from '@/components/budget/WaiverBudgetCard';
import { StrategicSuggestions } from '@/components/suggestions/StrategicSuggestions';
import { TeamSelectionModal } from '@/components/team/TeamSelectionModal';
import {
  TrophyIcon,
  UsersIcon,
  ChartBarIcon,
  CogIcon,
  ArrowLeftIcon,
  ExclamationTriangleIcon,
  CalendarIcon,
  FireIcon,
  ShieldCheckIcon,
} from '@heroicons/react/24/outline';
import { formatDate } from '@/utils';

export const LeagueDetailPage: React.FC = () => {
  const { leagueId } = useParams<{ leagueId: string }>();
  const navigate = useNavigate();
  const [showDisconnectModal, setShowDisconnectModal] = useState(false);
  const [showTeamSelectionModal, setShowTeamSelectionModal] = useState(false);

  const {
    data: league,
    isLoading: leagueLoading,
    error: leagueError,
  } = useLeague(parseInt(leagueId || '0', 10));

  const {
    data: teams,
    isLoading: teamsLoading,
    error: teamsError,
  } = useLeagueTeams(parseInt(leagueId || '0', 10));

  const { data: currentUser } = useCurrentUser();
  const disconnectLeague = useDisconnectLeague();
  const syncLeague = useSyncLeague();

  const { data: matchups, isLoading: matchupsLoading } = useMatchups(parseInt(leagueId || '0', 10), league?.current_week);
  const { data: waiverBudgets, isLoading: budgetsLoading } = useWaiverBudgets(parseInt(leagueId || '0', 10));

  // Find user's team by owner_user_id
  const userTeam = teams?.find(team => team.owner_user_id === currentUser?.id);

  // Check if user needs to select their team after sync
  useEffect(() => {
    if (teams && teams.length > 0 && !userTeam && currentUser) {
      // Show team selection modal if no team is claimed by the user
      setShowTeamSelectionModal(true);
    }
  }, [teams, userTeam, currentUser]);

  const handleSync = async () => {
    if (!league) return;

    try {
      await syncLeague.mutateAsync(league.id);
      // After sync, the useEffect will trigger team selection modal if needed
    } catch (error) {
      console.error('Failed to sync league:', error);
    }
  };

  const handleDisconnect = async () => {
    if (!league) return;

    try {
      await disconnectLeague.mutateAsync(league.id);
      navigate('/dashboard');
    } catch (error) {
      console.error('Failed to disconnect league:', error);
    }
  };

  if (leagueLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <LoadingSpinner size="lg" className="mt-12" />
      </div>
    );
  }

  if (leagueError || !league) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Card>
          <CardContent>
            <div className="text-center py-12">
              <ExclamationTriangleIcon className="h-12 w-12 text-red-500 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">League Not Found</h3>
              <p className="text-gray-600 mb-4">
                The league you're looking for doesn't exist or you don't have access to it.
              </p>
              <Link to="/dashboard">
                <Button>Back to Dashboard</Button>
              </Link>
            </div>
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
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate('/dashboard')}
            className="mr-4"
          >
            <ArrowLeftIcon className="h-4 w-4 mr-1" />
            Back to Dashboard
          </Button>
        </div>
        
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              {league.name}
            </h1>
            <div className="flex items-center space-x-4 text-sm text-gray-600">
              <span className="flex items-center">
                <UsersIcon className="h-4 w-4 mr-1" />
                {league.size} teams
              </span>
              <span className="flex items-center">
                <CalendarIcon className="h-4 w-4 mr-1" />
                {league.season_year} Season
              </span>
              <span className="flex items-center">
                <FireIcon className="h-4 w-4 mr-1" />
                Week {league.current_week}
              </span>
              <span className="flex items-center capitalize">
                <ChartBarIcon className="h-4 w-4 mr-1" />
                {league.scoring_type} scoring
              </span>
            </div>
          </div>
          
          <div className="mt-4 lg:mt-0 flex space-x-3">
            <Button 
              variant="secondary" 
              size="sm" 
              onClick={handleSync}
              disabled={syncLeague.isLoading}
            >
              <CogIcon className="h-4 w-4 mr-2" />
              {syncLeague.isLoading ? 'Syncing...' : 'Sync Data'}
            </Button>
            <Button
              variant="danger"
              size="sm"
              onClick={() => setShowDisconnectModal(true)}
            >
              Disconnect League
            </Button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* League Info */}
        <div className="lg:col-span-2 space-y-6">
          {/* League Stats */}
          <Card>
            <CardHeader>
              <CardTitle>League Overview</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="text-center p-4 bg-blue-50 rounded-lg">
                  <div className="text-2xl font-bold text-blue-600">{league.size}</div>
                  <div className="text-sm text-blue-800">Teams</div>
                </div>
                <div className="text-center p-4 bg-green-50 rounded-lg">
                  <div className="text-2xl font-bold text-green-600">{league.current_week}</div>
                  <div className="text-sm text-green-800">Current Week</div>
                </div>
                <div className="text-center p-4 bg-purple-50 rounded-lg">
                  <div className="text-2xl font-bold text-purple-600">{league.season_year}</div>
                  <div className="text-sm text-purple-800">Season</div>
                </div>
                <div className="text-center p-4 bg-orange-50 rounded-lg">
                  <div className="text-2xl font-bold text-orange-600">
                    {league.is_public ? 'Public' : 'Private'}
                  </div>
                  <div className="text-sm text-orange-800">League Type</div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Current Week Matchups */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <TrophyIcon className="h-5 w-5 mr-2" />
                Week {league.current_week} Matchups
              </CardTitle>
            </CardHeader>
            <CardContent>
              {matchupsLoading ? (
                <div className="flex justify-center py-8">
                  <LoadingSpinner size="sm" />
                </div>
              ) : matchups && matchups.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {matchups.map((matchup) => (
                    <MatchupCard 
                      key={matchup.id} 
                      matchup={matchup} 
                      userTeamId={userTeam?.id}
                    />
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-gray-600">
                  No matchups available for this week
                </div>
              )}
            </CardContent>
          </Card>

          {/* Waiver Budgets */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <ChartBarIcon className="h-5 w-5 mr-2" />
                Waiver Wire Budgets
              </CardTitle>
            </CardHeader>
            <CardContent>
              {budgetsLoading ? (
                <div className="flex justify-center py-8">
                  <LoadingSpinner size="sm" />
                </div>
              ) : waiverBudgets && waiverBudgets.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {waiverBudgets.map((budget) => (
                    <WaiverBudgetCard 
                      key={budget.team_id} 
                      budget={budget}
                      userTeamId={userTeam?.id}
                    />
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-gray-600">
                  No budget information available
                </div>
              )}
            </CardContent>
          </Card>

          {/* Strategic Suggestions */}
          <StrategicSuggestions 
            league={league} 
            userTeamId={userTeam?.id}
          />

          {/* Teams */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <UsersIcon className="h-5 w-5 mr-2" />
                Teams
                {teams && <span className="ml-2 text-sm font-normal text-gray-500">({teams.length})</span>}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {teamsLoading ? (
                <div className="flex justify-center py-8">
                  <LoadingSpinner size="sm" />
                </div>
              ) : teamsError ? (
                <div className="text-center py-8 text-gray-600">
                  Failed to load teams
                </div>
              ) : teams && teams.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {teams.map((team) => (
                    <Link 
                      key={team.id} 
                      to={`/leagues/${leagueId}/teams/${team.id}`}
                      className="block"
                    >
                      <div className="p-4 border rounded-lg hover:bg-gray-50 hover:shadow-md transition-all cursor-pointer border-l-4 border-l-blue-500">
                        <div className="flex items-center space-x-4">
                          {/* Team Logo */}
                          <div className="flex-shrink-0">
                            <img
                              src={team.logo_url}
                              alt={`${team.name || team.abbreviation} logo`}
                              className="w-12 h-12 rounded-full object-cover bg-gray-100"
                              onError={(e) => {
                                const target = e.target as HTMLImageElement;
                                target.style.display = 'none';
                              }}
                            />
                            <div className="w-12 h-12 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-bold text-sm">
                              {team.abbreviation || team.name?.charAt(0) || '?'}
                            </div>
                          </div>
                          
                          {/* Team Info */}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center justify-between">
                              <div>
                                <h4 className="font-semibold text-gray-900 text-lg">
                                  {team.name || `Team ${team.abbreviation}`}
                                </h4>
                                <p className="text-sm text-gray-500 mb-1">
                                  {team.abbreviation}
                                </p>
                                <div className="flex items-center space-x-3 text-sm">
                                  <span className="font-medium text-gray-900">
                                    {team.wins}-{team.losses}
                                    {team.ties > 0 && `-${team.ties}`}
                                  </span>
                                  <span className="text-green-600 font-medium">
                                    {team.points_for.toFixed(1)} PF
                                  </span>
                                  <span className="text-red-500">
                                    {team.points_against.toFixed(1)} PA
                                  </span>
                                </div>
                              </div>
                              
                              {/* Record Badge */}
                              <div className="text-right">
                                <div className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                                  team.wins > team.losses 
                                    ? 'bg-green-100 text-green-800'
                                    : team.wins < team.losses
                                    ? 'bg-red-100 text-red-800'
                                    : 'bg-gray-100 text-gray-800'
                                }`}>
                                  {team.wins > team.losses ? 'Winning' : team.wins < team.losses ? 'Losing' : 'Tied'}
                                </div>
                                <div className="text-xs text-gray-500 mt-1">
                                  Click to view roster
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </Link>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-gray-600">
                  No teams found. Try syncing your league data.
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* League Actions */}
          <Card>
            <CardHeader>
              <CardTitle>Actions</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <Button 
                  fullWidth 
                  variant="secondary" 
                  size="sm"
                  onClick={() => setShowTeamSelectionModal(true)}
                >
                  <UsersIcon className="h-4 w-4 mr-2" />
                  {userTeam ? 'Change My Team' : 'Select My Team'}
                </Button>
                <Link to={`/leagues/${league.id}/trades`} className="block">
                  <Button fullWidth variant="secondary" size="sm">
                    <ChartBarIcon className="h-4 w-4 mr-2" />
                    Trade Analyzer
                  </Button>
                </Link>
                <Link to={`/leagues/${league.id}/players`} className="block">
                  <Button fullWidth variant="secondary" size="sm">
                    <UsersIcon className="h-4 w-4 mr-2" />
                    Player Search
                  </Button>
                </Link>
                <Link to={`/leagues/${league.id}/roster`} className="block">
                  <Button fullWidth variant="secondary" size="sm">
                    <TrophyIcon className="h-4 w-4 mr-2" />
                    My Roster
                  </Button>
                </Link>
              </div>
            </CardContent>
          </Card>

          {/* League Info */}
          <Card>
            <CardHeader>
              <CardTitle>League Details</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">ESPN League ID:</span>
                  <span className="font-mono">{league.espn_league_id}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Your Team:</span>
                  <span className={userTeam ? "text-blue-600 font-medium" : "text-gray-400"}>
                    {userTeam ? userTeam.name : 'Not selected'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Connected:</span>
                  <span>{formatDate(league.created_at)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Last Synced:</span>
                  <span>
                    {league.last_synced ? formatDate(league.last_synced) : 'Never'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Status:</span>
                  <span className="flex items-center">
                    <ShieldCheckIcon className="h-4 w-4 text-green-500 mr-1" />
                    {league.is_active ? 'Active' : 'Inactive'}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Disconnect Modal */}
      {showDisconnectModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <Card className="max-w-md w-full">
            <CardHeader>
              <CardTitle className="text-red-600 flex items-center">
                <ExclamationTriangleIcon className="h-5 w-5 mr-2" />
                Disconnect League
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-600 mb-6">
                Are you sure you want to disconnect "{league.name}"? This will remove all associated data and cannot be undone.
              </p>
              <div className="flex space-x-3">
                <Button
                  variant="danger"
                  onClick={handleDisconnect}
                  disabled={disconnectLeague.isLoading}
                  className="flex-1"
                >
                  {disconnectLeague.isLoading ? (
                    <>
                      <LoadingSpinner size="sm" className="mr-2" />
                      Disconnecting...
                    </>
                  ) : (
                    'Disconnect'
                  )}
                </Button>
                <Button
                  variant="ghost"
                  onClick={() => setShowDisconnectModal(false)}
                  className="flex-1"
                >
                  Cancel
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Team Selection Modal */}
      <TeamSelectionModal
        isOpen={showTeamSelectionModal}
        onClose={() => setShowTeamSelectionModal(false)}
        teams={teams || []}
        leagueId={parseInt(leagueId || '0', 10)}
      />
    </div>
  );
};