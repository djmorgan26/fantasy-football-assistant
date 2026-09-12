import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useLeague, useDisconnectLeague, useSyncLeague } from '@/hooks/useLeagues';
import { useLeagueTeams } from '@/hooks/useTeams';
import { useMatchups } from '@/hooks/useMatchups';
import { useWaiverBudgets } from '@/hooks/useWaiverBudgets';
import { useCurrentUser } from '@/hooks/useAuth';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { Modal } from '@/components/ui/Modal';
import { EmptyState } from '@/components/ui/EmptyState';
import { Skeleton, SkeletonCard } from '@/components/ui/Skeleton';
import { WeeklyRecap } from '@/components/recap/WeeklyRecap';
import { MatchupCard } from '@/components/matchups/MatchupCard';
import { WaiverBudgetCard } from '@/components/budget/WaiverBudgetCard';
import { StrategicSuggestions } from '@/components/suggestions/StrategicSuggestions';
import { TeamSelectionModal } from '@/components/team/TeamSelectionModal';
import {
  TrophyIcon,
  UsersIcon,
  ChartBarIcon,
  CogIcon,
  ExclamationTriangleIcon,
  CalendarIcon,
  FireIcon,
  ShieldCheckIcon,
  BoltIcon,
  NewspaperIcon,
} from '@heroicons/react/24/outline';
import { PageContainer, PageHeader } from '@/components/layout/Page';
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
      <PageContainer>
        <div className="mb-8 space-y-3">
          <Skeleton className="h-9 w-2/3" />
          <Skeleton className="h-4 w-1/2" />
        </div>
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="space-y-6 lg:col-span-2">
            <SkeletonCard />
            <SkeletonCard />
          </div>
          <div className="space-y-6">
            <SkeletonCard />
            <SkeletonCard />
          </div>
        </div>
      </PageContainer>
    );
  }

  if (leagueError || !league) {
    return (
      <PageContainer>
        <Card>
          <EmptyState
            icon={ExclamationTriangleIcon}
            variant="error"
            title="League Not Found"
            description="The league you're looking for doesn't exist or you don't have access to it."
            action={
              <Link to="/dashboard">
                <Button>Back to Dashboard</Button>
              </Link>
            }
          />
        </Card>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <PageHeader
        backTo="/dashboard"
        backLabel="Back to Dashboard"
        title={league.name}
        subtitle={
          <span className="flex flex-wrap items-center gap-x-4 gap-y-1">
            <span className="flex items-center">
              <UsersIcon className="mr-1 h-4 w-4" />
              {league.size} teams
            </span>
            <span className="flex items-center">
              <CalendarIcon className="mr-1 h-4 w-4" />
              {league.season_year} Season
            </span>
            <span className="flex items-center">
              <FireIcon className="mr-1 h-4 w-4" />
              Week {league.current_week}
            </span>
            <span className="flex items-center capitalize">
              <ChartBarIcon className="mr-1 h-4 w-4" />
              {league.scoring_type} scoring
            </span>
          </span>
        }
        actions={
          <>
            <Button
              variant="secondary"
              size="sm"
              onClick={handleSync}
              disabled={syncLeague.isLoading}
            >
              <CogIcon className="mr-2 h-4 w-4" />
              {syncLeague.isLoading ? 'Syncing...' : 'Sync Data'}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setShowTeamSelectionModal(true)}
            >
              <UsersIcon className="mr-2 h-4 w-4" />
              {userTeam ? 'Change Team' : 'Select Team'}
            </Button>
          </>
        }
      />

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
                <div className="rounded-lg bg-surface-sunken p-4 text-center">
                  <div className="font-display text-2xl font-bold text-brand tabular">{league.size}</div>
                  <div className="mt-1 text-sm text-fg-muted">Teams</div>
                </div>
                <div className="rounded-lg bg-surface-sunken p-4 text-center">
                  <div className="font-display text-2xl font-bold text-brand tabular">{league.current_week}</div>
                  <div className="mt-1 text-sm text-fg-muted">Current Week</div>
                </div>
                <div className="rounded-lg bg-surface-sunken p-4 text-center">
                  <div className="font-display text-2xl font-bold text-brand tabular">{league.season_year}</div>
                  <div className="mt-1 text-sm text-fg-muted">Season</div>
                </div>
                <div className="rounded-lg bg-surface-sunken p-4 text-center">
                  <div className="font-display text-2xl font-bold text-brand">
                    {league.is_public ? 'Public' : 'Private'}
                  </div>
                  <div className="mt-1 text-sm text-fg-muted">League Type</div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Weekly Recap - AI-Generated Roast Report */}
          <WeeklyRecap
            leagueId={league.id}
            leagueName={league.name}
            currentWeek={league.current_week}
          />

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
                <EmptyState
                  icon={TrophyIcon}
                  title="No matchups available"
                  description="There are no matchups for this week yet."
                />
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
                <EmptyState
                  icon={ChartBarIcon}
                  title="No budget information"
                  description="Waiver budget data isn't available for this league yet."
                />
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
                {teams && <span className="ml-2 text-sm font-normal text-fg-muted">({teams.length})</span>}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {teamsLoading ? (
                <div className="flex justify-center py-8">
                  <LoadingSpinner size="sm" />
                </div>
              ) : teamsError ? (
                <EmptyState
                  icon={UsersIcon}
                  variant="error"
                  title="Failed to load teams"
                  description="We couldn't load the teams for this league. Try syncing again."
                />
              ) : teams && teams.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {teams.map((team) => (
                    <Link 
                      key={team.id} 
                      to={`/leagues/${leagueId}/teams/${team.id}`}
                      className="block"
                    >
                      <div className="rounded-lg border border-border border-l-4 border-l-brand bg-surface-raised p-4 transition-all hover:bg-surface-sunken hover:shadow-elevation-3">
                        <div className="flex items-center gap-3 sm:gap-4">
                          {/* Team Logo */}
                          <div className="flex-shrink-0">
                            <img
                              src={team.logo_url}
                              alt={`${team.name || team.abbreviation} logo`}
                              className="w-12 h-12 rounded-full object-cover bg-surface-sunken"
                              onError={(e) => {
                                const target = e.target as HTMLImageElement;
                                target.style.display = 'none';
                              }}
                            />
                            <div className="w-12 h-12 rounded-full bg-gradient-to-br from-brand to-primary-700 flex items-center justify-center text-brand-fg font-bold text-sm">
                              {team.abbreviation || team.name?.charAt(0) || '?'}
                            </div>
                          </div>

                          {/* Team Info */}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-start justify-between gap-3">
                              <div className="min-w-0">
                                <h4 className="truncate font-semibold text-fg text-base sm:text-lg">
                                  {team.name || `Team ${team.abbreviation}`}
                                </h4>
                                <p className="text-sm text-fg-muted mb-1">
                                  {team.abbreviation}
                                </p>
                                <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
                                  <span className="font-medium text-fg tabular">
                                    {team.wins}-{team.losses}
                                    {team.ties > 0 && `-${team.ties}`}
                                  </span>
                                  <span className="text-success-600 font-medium tabular">
                                    {team.points_for.toFixed(1)} PF
                                  </span>
                                  <span className="text-error-500 tabular">
                                    {team.points_against.toFixed(1)} PA
                                  </span>
                                </div>
                              </div>

                              {/* Record Badge */}
                              <div className="shrink-0 text-right">
                                <Badge
                                  size="sm"
                                  variant={
                                    team.wins > team.losses
                                      ? 'success'
                                      : team.wins < team.losses
                                      ? 'error'
                                      : 'default'
                                  }
                                >
                                  {team.wins > team.losses ? 'Winning' : team.wins < team.losses ? 'Losing' : 'Tied'}
                                </Badge>
                                <div className="mt-1 hidden text-xs text-fg-muted sm:block">
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
                <EmptyState
                  icon={UsersIcon}
                  title="No teams found"
                  description="Try syncing your league data to load teams."
                  action={
                    <Button size="sm" variant="secondary" onClick={handleSync} disabled={syncLeague.isLoading}>
                      <CogIcon className="h-4 w-4 mr-2" />
                      {syncLeague.isLoading ? 'Syncing...' : 'Sync Data'}
                    </Button>
                  }
                />
              )}
            </CardContent>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* League Actions — the mobile tab bar covers these destinations, so
              this card is desktop-only rather than a second copy of the nav. */}
          <Card className="hidden lg:block">
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
                <Link to={`/leagues/${league.id}/draft`} className="block">
                  <Button fullWidth size="sm">
                    <BoltIcon className="h-4 w-4 mr-2" />
                    Draft Room
                  </Button>
                </Link>
                <Link to={`/leagues/${league.id}/press-box`} className="block">
                  <Button fullWidth size="sm">
                    <NewspaperIcon className="h-4 w-4 mr-2" />
                    Press Box
                  </Button>
                </Link>
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
                <div className="flex flex-wrap justify-between gap-x-4 gap-y-0.5">
                  <span className="text-fg-muted">ESPN League ID:</span>
                  <span className="font-mono text-fg tabular">{league.espn_league_id}</span>
                </div>
                <div className="flex flex-wrap justify-between gap-x-4 gap-y-0.5">
                  <span className="text-fg-muted">Your Team:</span>
                  <span className={userTeam ? "text-brand font-medium" : "text-fg-subtle"}>
                    {userTeam ? userTeam.name : 'Not selected'}
                  </span>
                </div>
                <div className="flex flex-wrap justify-between gap-x-4 gap-y-0.5">
                  <span className="text-fg-muted">Connected:</span>
                  <span className="text-fg">{formatDate(league.created_at)}</span>
                </div>
                <div className="flex flex-wrap justify-between gap-x-4 gap-y-0.5">
                  <span className="text-fg-muted">Last Synced:</span>
                  <span className="text-fg">
                    {league.last_synced ? formatDate(league.last_synced) : 'Never'}
                  </span>
                </div>
                <div className="flex flex-wrap justify-between gap-x-4 gap-y-0.5">
                  <span className="text-fg-muted">Status:</span>
                  <span className="flex items-center text-fg">
                    <ShieldCheckIcon className="h-4 w-4 text-success-500 mr-1" />
                    {league.is_active ? 'Active' : 'Inactive'}
                  </span>
                </div>
              </div>

              <div className="mt-5 border-t border-border pt-4">
                <Button
                  fullWidth
                  variant="ghost"
                  size="sm"
                  className="text-error-600 hover:bg-error-50 dark:hover:bg-error-900/20"
                  onClick={() => setShowDisconnectModal(true)}
                >
                  Disconnect League
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Disconnect Modal */}
      <Modal
        isOpen={showDisconnectModal}
        onClose={() => setShowDisconnectModal(false)}
        size="sm"
        title={
          <span className="flex items-center text-error-600">
            <ExclamationTriangleIcon className="h-5 w-5 mr-2" />
            Disconnect League
          </span>
        }
        footer={
          <>
            <Button
              variant="ghost"
              onClick={() => setShowDisconnectModal(false)}
            >
              Cancel
            </Button>
            <Button
              variant="danger"
              onClick={handleDisconnect}
              disabled={disconnectLeague.isLoading}
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
          </>
        }
      >
        <p className="text-fg-muted">
          Are you sure you want to disconnect "{league.name}"? This will remove all associated data and cannot be undone.
        </p>
      </Modal>

      {/* Team Selection Modal */}
      <TeamSelectionModal
        isOpen={showTeamSelectionModal}
        onClose={() => setShowTeamSelectionModal(false)}
        teams={teams || []}
        leagueId={parseInt(leagueId || '0', 10)}
      />
    </PageContainer>
  );
};