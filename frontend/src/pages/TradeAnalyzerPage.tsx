import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useLeague } from '@/hooks/useLeagues';
import { useLeagueTeams } from '@/hooks/useTeams';
import { useCurrentUser } from '@/hooks/useAuth';
import { useAnalyzeTrade } from '@/hooks/useTrades';
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  Button,
  Input,
  Select,
  Progress,
  Badge,
  EmptyState,
  Skeleton,
  SkeletonText,
  LoadingSpinner,
} from '@/components/ui';
import type { SelectOption } from '@/components/ui';
import { Team, TradeAnalysisResponse } from '@/types';
import {
  ArrowLeftIcon,
  ArrowsRightLeftIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline';

export const TradeAnalyzerPage: React.FC = () => {
  const { leagueId } = useParams<{ leagueId: string }>();
  const { data: league } = useLeague(parseInt(leagueId || '0', 10));
  const { data: teams } = useLeagueTeams(parseInt(leagueId || '0', 10));
  const { data: currentUser } = useCurrentUser();

  const [selectedTeam1, setSelectedTeam1] = useState<Team | null>(null);
  const [selectedTeam2, setSelectedTeam2] = useState<Team | null>(null);
  const [team1Players, setTeam1Players] = useState<number[]>([]);
  const [team2Players, setTeam2Players] = useState<number[]>([]);
  const [analysis, setAnalysis] = useState<TradeAnalysisResponse | null>(null);

  const analyzeTradeMutation = useAnalyzeTrade();

  const handleAnalyzeTrade = async () => {
    if (
      !selectedTeam1 ||
      !selectedTeam2 ||
      selectedTeam1.espn_team_id === undefined ||
      selectedTeam2.espn_team_id === undefined ||
      team1Players.length === 0 ||
      team2Players.length === 0 ||
      !league
    ) {
      return;
    }

    try {
      const result = await analyzeTradeMutation.mutateAsync({
        league_id: league.id,
        proposing_team_id: selectedTeam1.espn_team_id,
        receiving_team_id: selectedTeam2.espn_team_id,
        give_players: team1Players,
        receive_players: team2Players,
      });

      setAnalysis(result);
    } catch (error) {
      // Error is handled by the mutation hook
    }
  };

  const resetAnalysis = () => {
    setSelectedTeam1(null);
    setSelectedTeam2(null);
    setTeam1Players([]);
    setTeam2Players([]);
    setAnalysis(null);
  };

  const teamLabel = (team: Team) =>
    `${team.name}${team.owner_user_id === currentUser?.id ? ' (You)' : ''}`;

  const team1Options: SelectOption[] =
    teams?.map((team) => ({ value: String(team.id), label: teamLabel(team) })) ?? [];
  const team2Options: SelectOption[] =
    teams
      ?.filter((t) => t.id !== selectedTeam1?.id)
      .map((team) => ({ value: String(team.id), label: teamLabel(team) })) ?? [];

  const isAnalyzing = analyzeTradeMutation.isLoading;

  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center mb-4">
          <Link
            to={`/leagues/${leagueId}`}
            className="flex items-center text-fg-muted transition-colors hover:text-fg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
          >
            <ArrowLeftIcon className="h-4 w-4 mr-1" />
            Back to League
          </Link>
        </div>

        <div className="flex items-center">
          <ArrowsRightLeftIcon className="h-8 w-8 text-brand mr-3" />
          <div>
            <h1 className="text-display-sm text-fg">
              Trade Analyzer
            </h1>
            <p className="text-fg-muted">
              Analyze potential trades between teams in {league?.name}
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Team Selection */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Select Teams</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {/* Team 1 Selection */}
                <Select
                  fullWidth
                  label="Team 1 (Trading away players)"
                  placeholder="Select a team..."
                  value={selectedTeam1 ? String(selectedTeam1.id) : ''}
                  options={team1Options}
                  onChange={(value) => {
                    const team = teams?.find((t) => t.id === parseInt(value));
                    setSelectedTeam1(team || null);
                    setTeam1Players([]);
                  }}
                />

                {/* Team 2 Selection */}
                <Select
                  fullWidth
                  label="Team 2 (Trading away players)"
                  placeholder="Select a team..."
                  value={selectedTeam2 ? String(selectedTeam2.id) : ''}
                  options={team2Options}
                  onChange={(value) => {
                    const team = teams?.find((t) => t.id === parseInt(value));
                    setSelectedTeam2(team || null);
                    setTeam2Players([]);
                  }}
                />
              </div>
            </CardContent>
          </Card>

          {/* Player Selection */}
          {selectedTeam1 && selectedTeam2 && (
            <Card>
              <CardHeader>
                <CardTitle>Select Players</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-fg mb-2">
                      Players from {selectedTeam1.name}
                    </label>
                    <div className="space-y-2">
                      {/* Player ID inputs - In a real implementation, you'd have a player selector */}
                      {[1, 2, 3].map(i => (
                        <Input
                          key={i}
                          fullWidth
                          type="number"
                          placeholder={`ESPN Player ID ${i}`}
                          onChange={(e) => {
                            const value = e.target.value ? parseInt(e.target.value) : null;
                            const newPlayers = [...team1Players];
                            if (value) {
                              newPlayers[i-1] = value;
                            } else {
                              newPlayers.splice(i-1, 1);
                            }
                            setTeam1Players(newPlayers.filter(p => p));
                          }}
                        />
                      ))}
                      <p className="text-xs text-fg-muted">
                        Enter ESPN Player IDs. You can find these by inspecting the roster endpoints.
                      </p>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-fg mb-2">
                      Players from {selectedTeam2.name}
                    </label>
                    <div className="space-y-2">
                      {/* Player ID inputs - In a real implementation, you'd have a player selector */}
                      {[1, 2, 3].map(i => (
                        <Input
                          key={i}
                          fullWidth
                          type="number"
                          placeholder={`ESPN Player ID ${i}`}
                          onChange={(e) => {
                            const value = e.target.value ? parseInt(e.target.value) : null;
                            const newPlayers = [...team2Players];
                            if (value) {
                              newPlayers[i-1] = value;
                            } else {
                              newPlayers.splice(i-1, 1);
                            }
                            setTeam2Players(newPlayers.filter(p => p));
                          }}
                        />
                      ))}
                      <p className="text-xs text-fg-muted">
                        Enter ESPN Player IDs. You can find these by inspecting the roster endpoints.
                      </p>
                    </div>
                  </div>
                </div>

                <div className="mt-6 flex space-x-3">
                  <Button
                    onClick={handleAnalyzeTrade}
                    disabled={!selectedTeam1 || !selectedTeam2 || team1Players.length === 0 || team2Players.length === 0 || analyzeTradeMutation.isLoading}
                    className="flex-1"
                  >
                    {analyzeTradeMutation.isLoading ? (
                      <>
                        <LoadingSpinner size="sm" className="mr-2" />
                        Analyzing...
                      </>
                    ) : (
                      'Analyze Trade'
                    )}
                  </Button>
                  <Button
                    variant="ghost"
                    onClick={resetAnalysis}
                  >
                    Reset
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Analysis Results */}
        <div aria-live="polite">
          {isAnalyzing ? (
            <Card>
              <CardHeader>
                <CardTitle>Analyzing Trade…</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-6">
                  <div>
                    <Skeleton className="mb-2 h-4 w-32" />
                    <Skeleton className="h-2.5 w-full rounded-pill" />
                  </div>
                  <SkeletonText lines={2} />
                  <SkeletonText lines={3} />
                </div>
              </CardContent>
            </Card>
          ) : analysis ? (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  {analysis.fairness_score !== undefined ? (
                    analysis.fairness_score >= 70 ? (
                      <CheckCircleIcon className="h-5 w-5 text-success-600 mr-2" />
                    ) : analysis.fairness_score >= 40 ? (
                      <ExclamationTriangleIcon className="h-5 w-5 text-warning-600 mr-2" />
                    ) : (
                      <XCircleIcon className="h-5 w-5 text-error-600 mr-2" />
                    )
                  ) : analysis.is_valid ? (
                    <CheckCircleIcon className="h-5 w-5 text-brand mr-2" />
                  ) : (
                    <XCircleIcon className="h-5 w-5 text-error-600 mr-2" />
                  )}
                  Trade Analysis Results
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-6">
                  {/* Validity */}
                  {analysis.is_valid !== undefined && (
                    <Badge variant={analysis.is_valid ? 'success' : 'error'} size="sm">
                      {analysis.is_valid ? 'Valid Trade' : 'Invalid Trade'}
                    </Badge>
                  )}

                  {/* Fairness Score */}
                  {analysis.fairness_score !== undefined && (
                    <div>
                      <div className="flex justify-between items-center mb-2">
                        <span className="text-sm font-medium text-fg">Fairness Score</span>
                        <span className="text-sm font-bold text-fg tabular">
                          {analysis.fairness_score.toFixed(1)}/100
                        </span>
                      </div>
                      <Progress
                        value={analysis.fairness_score}
                        label="Fairness score"
                        barClassName={
                          analysis.fairness_score >= 70
                            ? 'bg-success-500'
                            : analysis.fairness_score >= 40
                            ? 'bg-warning-500'
                            : 'bg-error-500'
                        }
                      />
                    </div>
                  )}

                  {/* Value Difference */}
                  {analysis.value_difference !== undefined && (
                    <div>
                      <h4 className="font-medium text-fg mb-2">Value Assessment</h4>
                      <p className={`text-sm ${analysis.value_difference > 0 ? 'text-success-600' : analysis.value_difference < 0 ? 'text-error-600' : 'text-fg-muted'}`}>
                        {analysis.value_difference > 0 ? 'Favorable' : analysis.value_difference < 0 ? 'Unfavorable' : 'Neutral'}
                        {analysis.value_difference !== 0 && (
                          <span className="tabular">
                            {` (${Math.abs(analysis.value_difference).toFixed(1)} point difference)`}
                          </span>
                        )}
                      </p>
                    </div>
                  )}

                  {/* Analysis Summary */}
                  <div>
                    <h4 className="font-medium text-fg mb-2">Analysis Summary</h4>
                    <p className="text-sm text-fg-muted">{analysis.analysis_summary}</p>
                  </div>

                  {/* Recommendations */}
                  {analysis.recommendations && analysis.recommendations.length > 0 && (
                    <div>
                      <h4 className="font-medium text-fg mb-2">Recommendations</h4>
                      <ul className="space-y-1">
                        {analysis.recommendations.map((rec: string, index: number) => (
                          <li key={index} className="text-sm text-fg-muted flex items-start">
                            <span className="text-brand mr-2">•</span>
                            {rec}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          ) : analyzeTradeMutation.isError ? (
            <Card>
              <EmptyState
                icon={XCircleIcon}
                variant="error"
                title="Couldn't analyze trade"
                description="Something went wrong while analyzing this trade. Check the selected teams and player IDs, then try again."
              />
            </Card>
          ) : (
            <Card>
              <EmptyState
                icon={ArrowsRightLeftIcon}
                title="Ready to Analyze"
                description="Select two teams and their players to analyze the trade fairness."
              />
            </Card>
          )}
        </div>
      </div>
    </div>
  );
};
