import React from 'react';
import { Matchup } from '@/types';
import { Card, CardContent } from '@/components/ui/Card';
import { cn } from '@/utils';
import { StarIcon } from '@heroicons/react/24/solid';

interface MatchupCardProps {
  matchup: Matchup;
  userTeamId?: number;
  className?: string;
}

export const MatchupCard: React.FC<MatchupCardProps> = ({ 
  matchup, 
  userTeamId,
  className 
}) => {
  const isUserHome = matchup.home_team_id === userTeamId;
  const isUserAway = matchup.away_team_id === userTeamId;
  const userIsPlaying = isUserHome || isUserAway;
  
  const homeTeamName = matchup.home_team_name || 
    `${matchup.home_team_location || ''} ${matchup.home_team_nickname || ''}`.trim() || 
    'Team';
  const awayTeamName = matchup.away_team_name || 
    `${matchup.away_team_location || ''} ${matchup.away_team_nickname || ''}`.trim() || 
    'Team';
  
  // Determine favorite based on projected scores
  const homeProjected = matchup.home_projected_score || 0;
  const awayProjected = matchup.away_projected_score || 0;
  const homeFavorite = homeProjected > awayProjected && homeProjected > 0;
  const awayFavorite = awayProjected > homeProjected && awayProjected > 0;

  const getWinnerStyle = (isHome: boolean) => {
    const isWinner = matchup.winner === (isHome ? 'HOME' : 'AWAY');
    const isUser = userTeamId === (isHome ? matchup.home_team_id : matchup.away_team_id);
    
    if (matchup.winner === 'UNDECIDED') return '';
    
    if (isWinner) {
      return isUser ? 'bg-green-50 border-green-200' : 'bg-blue-50 border-blue-200';
    }
    return 'bg-gray-50 border-gray-200 opacity-75';
  };

  return (
    <Card className={cn(
      'overflow-hidden transition-all duration-200',
      userIsPlaying && 'ring-2 ring-primary-200',
      matchup.is_playoff && 'border-yellow-300 bg-yellow-50',
      className
    )}>
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-600">
            Week {matchup.week}
            {matchup.is_playoff && (
              <span className="ml-2 px-2 py-1 text-xs bg-yellow-200 text-yellow-800 rounded-full">
                Playoff
              </span>
            )}
          </span>
          {userIsPlaying && (
            <span className="text-xs px-2 py-1 bg-primary-100 text-primary-800 rounded-full">
              Your Matchup
            </span>
          )}
        </div>

        <div className="space-y-3">
          {/* Away Team */}
          <div className={cn(
            'flex items-center justify-between p-3 rounded-lg border',
            getWinnerStyle(false)
          )}>
            <div className="flex items-center space-x-3">
              <div className="flex items-center space-x-2">
                {awayFavorite && (
                  <StarIcon className="h-4 w-4 text-yellow-500" />
                )}
                <div className="flex flex-col">
                  <span className={cn(
                    'font-medium text-sm',
                    isUserAway && 'text-primary-700',
                    matchup.winner === 'AWAY' && 'font-bold'
                  )}>
                    {awayTeamName}
                  </span>
                  <span className="text-xs text-gray-500">
                    {awayProjected > 0 ? `Proj: ${awayProjected.toFixed(1)}` : 'No projection'}
                  </span>
                </div>
              </div>
            </div>
            <div className="text-right">
              <div className={cn(
                'text-lg font-bold',
                isUserAway && 'text-primary-700',
                matchup.winner === 'AWAY' && 'text-green-600'
              )}>
                {matchup.away_score.toFixed(1)}
              </div>
              <div className="text-xs text-gray-500">Actual</div>
            </div>
          </div>

          {/* VS Divider */}
          <div className="text-center">
            <span className="text-xs text-gray-400 bg-white px-2 py-1 rounded border">
              VS
            </span>
          </div>

          {/* Home Team */}
          <div className={cn(
            'flex items-center justify-between p-3 rounded-lg border',
            getWinnerStyle(true)
          )}>
            <div className="flex items-center space-x-3">
              <div className="flex items-center space-x-2">
                {homeFavorite && (
                  <StarIcon className="h-4 w-4 text-yellow-500" />
                )}
                <div className="flex flex-col">
                  <span className={cn(
                    'font-medium text-sm',
                    isUserHome && 'text-primary-700',
                    matchup.winner === 'HOME' && 'font-bold'
                  )}>
                    {homeTeamName}
                  </span>
                  <span className="text-xs text-gray-500">
                    {homeProjected > 0 ? `Proj: ${homeProjected.toFixed(1)}` : 'No projection'}
                  </span>
                </div>
              </div>
            </div>
            <div className="text-right">
              <div className={cn(
                'text-lg font-bold',
                isUserHome && 'text-primary-700',
                matchup.winner === 'HOME' && 'text-green-600'
              )}>
                {matchup.home_score.toFixed(1)}
              </div>
              <div className="text-xs text-gray-500">Actual</div>
            </div>
          </div>
        </div>

        {/* Result Summary */}
        {matchup.winner !== 'UNDECIDED' && (
          <div className="mt-3 pt-3 border-t border-gray-200">
            <div className="text-center">
              <span className={cn(
                'text-xs font-medium',
                matchup.winner === 'TIE' ? 'text-yellow-600' : 'text-gray-600'
              )}>
                {matchup.winner === 'TIE' 
                  ? 'Tied Game' 
                  : `${matchup.winner === 'HOME' ? homeTeamName : awayTeamName} Wins`
                }
              </span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};