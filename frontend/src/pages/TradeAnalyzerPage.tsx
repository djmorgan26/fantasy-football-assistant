import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useLeague } from '@/hooks/useLeagues';
import { useLeagueTeams } from '@/hooks/useTeams';
import { useCurrentUser } from '@/hooks/useAuth';
import { useAnalyzeTrade } from '@/hooks/useTrades';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
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

  const userTeam = teams?.find(team => team.owner_user_id === currentUser?.id);
  const analyzeTradeMutation = useAnalyzeTrade();

  const handleAnalyzeTrade = async () => {
    if (!selectedTeam1 || !selectedTeam2 || team1Players.length === 0 || team2Players.length === 0 || !league) {
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
        
        <div className="flex items-center">
          <ArrowsRightLeftIcon className="h-8 w-8 text-blue-600 mr-3" />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">
              Trade Analyzer
            </h1>
            <p className="text-gray-600">
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
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Team 1 (Trading away players)
                  </label>
                  <select
                    value={selectedTeam1?.id || ''}
                    onChange={(e) => {
                      const team = teams?.find(t => t.id === parseInt(e.target.value));
                      setSelectedTeam1(team || null);
                      setTeam1Players([]);
                    }}
                    className="w-full p-2 border rounded-lg"
                  >
                    <option value="">Select a team...</option>
                    {teams?.map(team => (
                      <option key={team.id} value={team.id}>
                        {team.name} {team.owner_user_id === currentUser?.id ? '(You)' : ''}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Team 2 Selection */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Team 2 (Trading away players)
                  </label>
                  <select
                    value={selectedTeam2?.id || ''}
                    onChange={(e) => {
                      const team = teams?.find(t => t.id === parseInt(e.target.value));
                      setSelectedTeam2(team || null);
                      setTeam2Players([]);
                    }}
                    className="w-full p-2 border rounded-lg"
                  >
                    <option value="">Select a team...</option>
                    {teams?.filter(t => t.id !== selectedTeam1?.id).map(team => (
                      <option key={team.id} value={team.id}>
                        {team.name} {team.owner_user_id === currentUser?.id ? '(You)' : ''}
                      </option>
                    ))}
                  </select>
                </div>
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
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Players from {selectedTeam1.name}
                    </label>
                    <div className="space-y-2">
                      {/* Player ID inputs - In a real implementation, you'd have a player selector */}
                      {[1, 2, 3].map(i => (
                        <input
                          key={i}
                          type="number"
                          placeholder={`ESPN Player ID ${i}`}
                          className="w-full p-2 border rounded-lg"
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
                      <p className="text-xs text-gray-500">
                        Enter ESPN Player IDs. You can find these by inspecting the roster endpoints.
                      </p>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Players from {selectedTeam2.name}
                    </label>
                    <div className="space-y-2">
                      {/* Player ID inputs - In a real implementation, you'd have a player selector */}
                      {[1, 2, 3].map(i => (
                        <input
                          key={i}
                          type="number"
                          placeholder={`ESPN Player ID ${i}`}
                          className="w-full p-2 border rounded-lg"
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
                      <p className="text-xs text-gray-500">
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
        <div>
          {analysis ? (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  {analysis.fairness_score !== undefined ? (
                    analysis.fairness_score >= 70 ? (
                      <CheckCircleIcon className="h-5 w-5 text-green-500 mr-2" />
                    ) : analysis.fairness_score >= 40 ? (
                      <ExclamationTriangleIcon className="h-5 w-5 text-yellow-500 mr-2" />
                    ) : (
                      <XCircleIcon className="h-5 w-5 text-red-500 mr-2" />
                    )
                  ) : analysis.is_valid ? (
                    <CheckCircleIcon className="h-5 w-5 text-blue-500 mr-2" />
                  ) : (
                    <XCircleIcon className="h-5 w-5 text-red-500 mr-2" />
                  )}
                  Trade Analysis Results
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-6">
                  {/* Fairness Score */}
                  {analysis.fairness_score !== undefined && (
                    <div>
                      <div className="flex justify-between items-center mb-2">
                        <span className="text-sm font-medium text-gray-700">Fairness Score</span>
                        <span className="text-sm font-bold">{analysis.fairness_score.toFixed(1)}/100</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div 
                          className={`h-2 rounded-full ${
                            analysis.fairness_score >= 70 ? 'bg-green-500' : 
                            analysis.fairness_score >= 40 ? 'bg-yellow-500' : 'bg-red-500'
                          }`}
                          style={{ width: `${Math.min(analysis.fairness_score, 100)}%` }}
                        ></div>
                      </div>
                    </div>
                  )}

                  {/* Value Difference */}
                  {analysis.value_difference !== undefined && (
                    <div>
                      <h4 className="font-medium text-gray-900 mb-2">Value Assessment</h4>
                      <p className={`text-sm ${analysis.value_difference > 0 ? 'text-green-600' : analysis.value_difference < 0 ? 'text-red-600' : 'text-gray-600'}`}>
                        {analysis.value_difference > 0 ? 'Favorable' : analysis.value_difference < 0 ? 'Unfavorable' : 'Neutral'} 
                        {analysis.value_difference !== 0 && ` (${Math.abs(analysis.value_difference).toFixed(1)} point difference)`}
                      </p>
                    </div>
                  )}

                  {/* Analysis Summary */}
                  <div>
                    <h4 className="font-medium text-gray-900 mb-2">Analysis Summary</h4>
                    <p className="text-sm text-gray-600">{analysis.analysis_summary}</p>
                  </div>

                  {/* Recommendations */}
                  {analysis.recommendations && analysis.recommendations.length > 0 && (
                    <div>
                      <h4 className="font-medium text-gray-900 mb-2">Recommendations</h4>
                      <ul className="space-y-1">
                        {analysis.recommendations.map((rec: string, index: number) => (
                          <li key={index} className="text-sm text-gray-600 flex items-start">
                            <span className="text-blue-500 mr-2">•</span>
                            {rec}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="text-center py-12">
                <ArrowsRightLeftIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  Ready to Analyze
                </h3>
                <p className="text-gray-600">
                  Select two teams and their players to analyze the trade fairness.
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
};