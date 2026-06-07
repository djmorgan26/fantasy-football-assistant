import React from 'react';
import { TeamBudgetSummary, WaiverTransaction } from '@/types';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Progress } from '@/components/ui/Progress';
import { cn } from '@/utils';
import { CurrencyDollarIcon } from '@heroicons/react/24/outline';

interface WaiverBudgetCardProps {
  budget: TeamBudgetSummary;
  userTeamId?: number;
  className?: string;
}

type BadgeVariant = 'default' | 'secondary' | 'success' | 'warning' | 'error';

const TransactionBadge: React.FC<{ transaction: WaiverTransaction }> = ({ transaction }) => {
  const getTypeVariant = (type: string): BadgeVariant => {
    switch (type) {
      case 'ADD':
        return 'success';
      case 'DROP':
        return 'error';
      case 'TRADE':
        return 'secondary';
      default:
        return 'default';
    }
  };

  const getStatusVariant = (status: string): BadgeVariant => {
    switch (status) {
      case 'SUCCESSFUL':
        return 'success';
      case 'FAILED':
        return 'error';
      case 'PENDING':
        return 'warning';
      default:
        return 'default';
    }
  };

  return (
    <div className="flex items-center justify-between p-2 bg-surface-sunken rounded text-sm">
      <div className="flex items-center space-x-2">
        <Badge variant={getTypeVariant(transaction.transaction_type)} size="sm">
          {transaction.transaction_type}
        </Badge>
        <span className="font-medium text-fg">{transaction.player_name}</span>
      </div>
      <div className="flex items-center space-x-2">
        {transaction.bid_amount > 0 && (
          <span className="text-fg-muted tabular">${transaction.bid_amount}</span>
        )}
        <Badge variant={getStatusVariant(transaction.status)} size="sm">
          {transaction.status}
        </Badge>
      </div>
    </div>
  );
};

export const WaiverBudgetCard: React.FC<WaiverBudgetCardProps> = ({ 
  budget, 
  userTeamId,
  className 
}) => {
  const isUserTeam = budget.team_id === userTeamId;
  const spentPercentage = Math.round((budget.spent_budget / budget.total_budget) * 100);
  const remainingPercentage = 100 - spentPercentage;

  const getBudgetHealthColor = () => {
    if (remainingPercentage >= 70) return 'text-success-600';
    if (remainingPercentage >= 40) return 'text-warning-600';
    return 'text-error-600';
  };

  const getBudgetHealthBg = () => {
    if (remainingPercentage >= 70) return 'bg-success-500';
    if (remainingPercentage >= 40) return 'bg-warning-500';
    return 'bg-error-500';
  };

  return (
    <Card className={cn(
      'transition-all duration-200',
      isUserTeam && 'ring-2 ring-brand bg-brand/5',
      className
    )}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">
            {budget.team_name}
            {isUserTeam && (
              <span className="ml-2 text-xs px-2 py-1 bg-brand/10 text-brand rounded-full">
                Your Team
              </span>
            )}
          </CardTitle>
          <CurrencyDollarIcon className="h-5 w-5 text-fg-subtle" />
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Budget Overview */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-fg-muted">Budget Remaining</span>
            <span className={cn('text-lg font-bold tabular', getBudgetHealthColor())}>
              ${budget.current_budget}
            </span>
          </div>

          {/* Budget Progress Bar */}
          <Progress
            value={remainingPercentage}
            barClassName={getBudgetHealthBg()}
            label={`${remainingPercentage}% of budget remaining`}
          />

          <div className="grid grid-cols-2 gap-4 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-fg-muted">Total:</span>
              <span className="font-medium text-fg tabular">${budget.total_budget}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-fg-muted">Spent:</span>
              <span className="font-medium text-error-600 tabular">${budget.spent_budget}</span>
            </div>
          </div>

          <div className="text-center">
            <span className="text-xs text-fg-subtle tabular">
              {spentPercentage}% of budget used
            </span>
          </div>
        </div>

        {/* Recent Transactions */}
        {budget.recent_transactions.length > 0 && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-medium text-fg">Recent Activity</h4>
              {budget.recent_transactions.some(t => t.status === 'PENDING') && (
                <Badge variant="warning" size="sm">
                  Pending
                </Badge>
              )}
            </div>
            
            <div className="space-y-2">
              {budget.recent_transactions.slice(0, 3).map((transaction) => (
                <TransactionBadge key={transaction.id} transaction={transaction} />
              ))}
            </div>
            
            {budget.recent_transactions.length > 3 && (
              <div className="text-center">
                <span className="text-xs text-fg-subtle tabular">
                  +{budget.recent_transactions.length - 3} more transactions
                </span>
              </div>
            )}
          </div>
        )}

        {budget.recent_transactions.length === 0 && (
          <div className="text-center py-4">
            <p className="text-sm text-fg-subtle">No recent activity</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
};