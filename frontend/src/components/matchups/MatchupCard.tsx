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
      return isUser
        ? 'bg-success-50 border-success-200 dark:bg-success-900/20 dark:border-success-800'
        : 'bg-brand/5 border-brand/30';
    }
    return 'bg-surface-sunken border-border opacity-75';
  };

  return (
    <Card className={cn(
      'overflow-hidden transition-all duration-200',
      userIsPlaying && 'ring-2 ring-brand',
      matchup.is_playoff && 'border-warning-300 bg-warning-50 dark:bg-warning-900/20',
      className
    )}>
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-fg-muted tabular">
            Week {matchup.week}
            {matchup.is_playoff && (
              <span className="ml-2 px-2 py-1 text-xs bg-warning-100 text-warning-800 dark:bg-warning-900/40 dark:text-warning-300 rounded-full">
                Playoff
              </span>
            )}
          </span>
          {userIsPlaying && (
            <span className="text-xs px-2 py-1 bg-brand/10 text-brand rounded-full">
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
                  <StarIcon className="h-4 w-4 text-warning-500" />
                )}
                <div className="flex flex-col">
                  <span className={cn(
                    'font-medium text-sm text-fg',
                    isUserAway && 'text-brand',
                    matchup.winner === 'AWAY' && 'font-bold'
                  )}>
                    {awayTeamName}
                  </span>
                  <span className="text-xs text-fg-subtle tabular">
                    {awayProjected > 0 ? `Proj: ${awayProjected.toFixed(1)}` : 'No projection'}
                  </span>
                </div>
              </div>
            </div>
            <div className="text-right">
              <div className={cn(
                'text-lg font-bold tabular text-fg',
                isUserAway && 'text-brand',
                matchup.winner === 'AWAY' && 'text-success-600'
              )}>
                {matchup.away_score.toFixed(1)}
              </div>
              <div className="text-xs text-fg-subtle">Actual</div>
            </div>
          </div>

          {/* VS Divider */}
          <div className="text-center">
            <span className="text-xs text-fg-subtle bg-surface-raised px-2 py-1 rounded border border-border">
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
                  <StarIcon className="h-4 w-4 text-warning-500" />
                )}
                <div className="flex flex-col">
                  <span className={cn(
                    'font-medium text-sm text-fg',
                    isUserHome && 'text-brand',
                    matchup.winner === 'HOME' && 'font-bold'
                  )}>
                    {homeTeamName}
                  </span>
                  <span className="text-xs text-fg-subtle tabular">
                    {homeProjected > 0 ? `Proj: ${homeProjected.toFixed(1)}` : 'No projection'}
                  </span>
                </div>
              </div>
            </div>
            <div className="text-right">
              <div className={cn(
                'text-lg font-bold tabular text-fg',
                isUserHome && 'text-brand',
                matchup.winner === 'HOME' && 'text-success-600'
              )}>
                {matchup.home_score.toFixed(1)}
              </div>
              <div className="text-xs text-fg-subtle">Actual</div>
            </div>
          </div>
        </div>

        {/* Result Summary */}
        {matchup.winner !== 'UNDECIDED' && (
          <div className="mt-3 pt-3 border-t border-border">
            <div className="text-center">
              <span className={cn(
                'text-xs font-medium',
                matchup.winner === 'TIE' ? 'text-warning-600' : 'text-fg-muted'
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