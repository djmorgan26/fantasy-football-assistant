import React from 'react';
import { TeamBudgetSummary, WaiverTransaction } from '@/types';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { cn } from '@/utils';
import { CurrencyDollarIcon } from '@heroicons/react/24/outline';

interface WaiverBudgetCardProps {
  budget: TeamBudgetSummary;
  userTeamId?: number;
  className?: string;
}

const TransactionBadge: React.FC<{ transaction: WaiverTransaction }> = ({ transaction }) => {
  const getTypeColor = (type: string) => {
    switch (type) {
      case 'ADD':
        return 'bg-green-100 text-green-800';
      case 'DROP':
        return 'bg-red-100 text-red-800';
      case 'TRADE':
        return 'bg-blue-100 text-blue-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'SUCCESSFUL':
        return 'bg-green-100 text-green-800';
      case 'FAILED':
        return 'bg-red-100 text-red-800';
      case 'PENDING':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="flex items-center justify-between p-2 bg-gray-50 rounded text-sm">
      <div className="flex items-center space-x-2">
        <Badge className={getTypeColor(transaction.transaction_type)} size="sm">
          {transaction.transaction_type}
        </Badge>
        <span className="font-medium">{transaction.player_name}</span>
      </div>
      <div className="flex items-center space-x-2">
        {transaction.bid_amount > 0 && (
          <span className="text-gray-600">${transaction.bid_amount}</span>
        )}
        <Badge className={getStatusColor(transaction.status)} size="sm">
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
    if (remainingPercentage >= 70) return 'text-green-600';
    if (remainingPercentage >= 40) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getBudgetHealthBg = () => {
    if (remainingPercentage >= 70) return 'bg-green-500';
    if (remainingPercentage >= 40) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  return (
    <Card className={cn(
      'transition-all duration-200',
      isUserTeam && 'ring-2 ring-primary-200 bg-primary-50',
      className
    )}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">
            {budget.team_name}
            {isUserTeam && (
              <span className="ml-2 text-xs px-2 py-1 bg-primary-100 text-primary-800 rounded-full">
                Your Team
              </span>
            )}
          </CardTitle>
          <CurrencyDollarIcon className="h-5 w-5 text-gray-400" />
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Budget Overview */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600">Budget Remaining</span>
            <span className={cn('text-lg font-bold', getBudgetHealthColor())}>
              ${budget.current_budget}
            </span>
          </div>
          
          {/* Budget Progress Bar */}
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className={cn('h-2 rounded-full transition-all duration-300', getBudgetHealthBg())}
              style={{ width: `${remainingPercentage}%` }}
            />
          </div>
          
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-gray-600">Total:</span>
              <span className="font-medium">${budget.total_budget}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-600">Spent:</span>
              <span className="font-medium text-red-600">${budget.spent_budget}</span>
            </div>
          </div>
          
          <div className="text-center">
            <span className="text-xs text-gray-500">
              {spentPercentage}% of budget used
            </span>
          </div>
        </div>

        {/* Recent Transactions */}
        {budget.recent_transactions.length > 0 && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-medium text-gray-700">Recent Activity</h4>
              {budget.recent_transactions.some(t => t.status === 'PENDING') && (
                <Badge className="bg-yellow-100 text-yellow-800" size="sm">
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
                <span className="text-xs text-gray-500">
                  +{budget.recent_transactions.length - 3} more transactions
                </span>
              </div>
            )}
          </div>
        )}

        {budget.recent_transactions.length === 0 && (
          <div className="text-center py-4">
            <p className="text-sm text-gray-500">No recent activity</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
};