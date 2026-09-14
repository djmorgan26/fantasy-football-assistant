import React from 'react';
import { useParams } from 'react-router-dom';
import {
  ArrowsRightLeftIcon,
  BanknotesIcon,
  CheckCircleIcon,
  ClipboardDocumentCheckIcon,
  ExclamationTriangleIcon,
  UserPlusIcon,
} from '@heroicons/react/24/outline';

import { PageContainer, PageHeader } from '@/components/layout/Page';
import { StrategicSuggestions } from '@/components/suggestions/StrategicSuggestions';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { EmptyState } from '@/components/ui/EmptyState';
import { Skeleton } from '@/components/ui/Skeleton';
import { ToolHeader } from '@/components/ui/ToolHeader';
import { useActionPlan } from '@/hooks/useActionPlan';
import { useCurrentUser } from '@/hooks/useAuth';
import { useLeagueTeams } from '@/hooks/useTeams';
import { ActionUrgency, RosterAction } from '@/types';
import { cn } from '@/utils';

/**
 * What to do about this roster, in the order it matters.
 *
 * A starter landing on IR is a guaranteed zero in a starting slot, and until
 * this page the app would show you the status and leave the rest to you: who
 * covers the slot, who is available to replace him properly, what to bid, and
 * whether the hole opens a trade. Each card answers all four for one problem.
 */
const URGENCY: Record<ActionUrgency, { label: string; chip: string; rail: string }> = {
  critical: {
    label: 'Critical',
    chip: 'bg-error-500/15 text-error-600 dark:text-error-400',
    rail: 'border-l-error-500',
  },
  high: {
    label: 'Act now',
    chip: 'bg-warning-500/15 text-warning-700 dark:text-warning-400',
    rail: 'border-l-warning-500',
  },
  medium: {
    label: 'Worth doing',
    chip: 'bg-accent/15 text-accent',
    rail: 'border-l-accent',
  },
  low: {
    label: 'Covered',
    chip: 'bg-brand/15 text-brand',
    rail: 'border-l-brand',
  },
};

const Section: React.FC<{
  icon: React.ComponentType<React.SVGProps<SVGSVGElement>>;
  title: string;
  children: React.ReactNode;
}> = ({ icon: Icon, title, children }) => (
  <div className="min-w-0">
    <div className="mb-1.5 flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-fg-subtle">
      <Icon className="h-3.5 w-3.5" />
      {title}
    </div>
    {children}
  </div>
);

const ActionCard: React.FC<{ action: RosterAction }> = ({ action }) => {
  const tone = URGENCY[action.urgency] ?? URGENCY.medium;
  const { hole, start_instead: swap, faab, waiver_targets: waivers, trades } = action;

  return (
    <div
      data-testid="action-card"
      className={cn(
        'rounded-card border border-border border-l-4 bg-surface-raised p-4',
        tone.rail
      )}
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <h3 className="font-display text-lg font-bold text-fg">
            {hole.player} is {hole.status.replace(/_/g, ' ').toLowerCase()}
          </h3>
          <p className="text-sm text-fg-muted">
            Your {hole.slot} slot scores 0 until you move someone into it.
          </p>
        </div>
        <span className={cn('shrink-0 rounded-pill px-2.5 py-1 text-xs font-semibold', tone.chip)}>
          {tone.label}
        </span>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 border-t border-border pt-4 sm:grid-cols-2">
        <Section icon={CheckCircleIcon} title="Start instead">
          {swap ? (
            <div>
              <div className="font-semibold text-fg">{swap.player}</div>
              <div className="text-sm text-fg-muted">
                {swap.position}
                {swap.team ? ` · ${swap.team}` : ''} · projected{' '}
                <span className="tabular">{swap.projected.toFixed(1)}</span>
              </div>
              {swap.last_week > 0 && (
                <div className="mt-0.5 text-xs text-brand">
                  Scored {swap.last_week.toFixed(1)} last week
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm text-error-600 dark:text-error-400">
              Nobody on your bench can legally start in that slot. You have to add
              someone.
            </p>
          )}
          {action.other_bench.length > 0 && (
            <p className="mt-1.5 text-xs text-fg-subtle">
              Also eligible:{' '}
              {action.other_bench.map((b) => `${b.player} (${b.projected.toFixed(1)})`).join(', ')}
            </p>
          )}
        </Section>

        <Section icon={UserPlusIcon} title="Available to add">
          {waivers.length === 0 ? (
            <p className="text-sm text-fg-muted">Nothing better than your bench is free.</p>
          ) : (
            <ul className="space-y-1">
              {waivers.map((w) => (
                <li key={`${w.player_id}-${w.player}`} className="text-sm">
                  <span className="font-medium text-fg">{w.player}</span>{' '}
                  <span className="text-fg-subtle">
                    {w.position}
                    {w.team ? ` · ${w.team}` : ''} · {w.projected.toFixed(1)}
                  </span>
                  {w.contested && (
                    <span className="ml-1.5 rounded-pill bg-warning-500/15 px-1.5 py-0.5 text-[10px] font-semibold text-warning-700 dark:text-warning-400">
                      {w.added_by.toLocaleString()} adds today
                    </span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </Section>

        {faab && (
          <Section icon={BanknotesIcon} title="What to bid">
            {faab.note ? (
              <p className="text-sm text-fg-muted">{faab.note}</p>
            ) : (
              <p className="text-sm text-fg-muted">
                Bid{' '}
                <span className="font-display font-bold text-fg tabular">
                  ${faab.suggested_bid}
                </span>{' '}
                of your <span className="tabular">${faab.remaining}</span> left. Do not go
                past <span className="tabular">${faab.max_sensible}</span> for one player
                this early.
              </p>
            )}
          </Section>
        )}

        {trades.length > 0 && (
          <Section icon={ArrowsRightLeftIcon} title="Trade angle">
            <ul className="space-y-1">
              {trades.map((t) => (
                <li key={t.team} className="text-sm text-fg-muted">
                  <span className="font-medium text-fg">{t.team}</span> is thin at{' '}
                  {t.they_need} and can spare a {t.they_can_spare}.
                </li>
              ))}
            </ul>
          </Section>
        )}
      </div>
    </div>
  );
};

export const GamePlanPage: React.FC = () => {
  const { leagueId } = useParams<{ leagueId: string }>();
  const id = Number(leagueId);
  const { data, isLoading, isError, error } = useActionPlan(id);

  // The strategic suggestions used to sit on the league overview, which meant
  // the two halves of "what should I do this week" lived on different pages.
  const { data: teams } = useLeagueTeams(id);
  const { data: currentUser } = useCurrentUser();
  const userTeam = teams?.find((team) => team.owner_user_id === currentUser?.id);

  return (
    <PageContainer>
      <PageHeader
        title="Game Plan"
        subtitle="What is wrong with this roster, and what to do about it"
      />

      {isLoading ? (
        <div className="space-y-4">
          <Skeleton className="h-24 w-full rounded-card" />
          <Skeleton className="h-64 w-full rounded-card" />
        </div>
      ) : isError || !data ? (
        <Card>
          <EmptyState
            icon={ClipboardDocumentCheckIcon}
            variant="error"
            title="Couldn't build a plan"
            description={error?.detail || 'Try again in a moment.'}
          />
        </Card>
      ) : (
        <>
          <ToolHeader
            className="mb-4"
            icon={ClipboardDocumentCheckIcon}
            title="Game Plan"
            context={`Week ${data.week}`}
            subtitle={
              data.actions.length > 0
                ? `${data.actions.length} ${
                    data.actions.length === 1 ? 'thing needs' : 'things need'
                  } your attention`
                : 'Nothing is broken'
            }
          />

          {data.summary && (
            <Card className="mb-6 border-brand/30 bg-brand/5">
              <CardContent className="p-4">
                <p className="whitespace-pre-wrap text-sm leading-relaxed text-fg">
                  {data.summary}
                </p>
              </CardContent>
            </Card>
          )}

          {data.all_clear ? (
            <Card>
              <EmptyState
                icon={CheckCircleIcon}
                title="Nothing to fix"
                description="Every starter is healthy and in a slot they can play. Enjoy it."
              />
            </Card>
          ) : (
            <div className="space-y-4">
              {data.actions.map((action) => (
                <ActionCard key={`${action.hole.player_id}-${action.hole.slot}`} action={action} />
              ))}
            </div>
          )}

          {data.risks.length > 0 && (
            <Card className="mt-6">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <ExclamationTriangleIcon className="h-5 w-5 text-warning-500" />
                  Worth watching
                </CardTitle>
                <p className="mt-1 text-sm text-fg-muted">
                  Not ruled out, so benching them may cost you more than starting them.
                </p>
              </CardHeader>
              <CardContent>
                <ul className="space-y-1.5">
                  {data.risks.map((r) => (
                    <li key={r.player} className="text-sm">
                      <span className="font-medium text-fg">{r.player}</span>{' '}
                      <span className="text-fg-subtle">
                        {r.slot} · {r.status.toLowerCase()} · projected{' '}
                        <span className="tabular">{r.projected.toFixed(1)}</span>
                      </span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}
        </>
      )}

      <StrategicSuggestions className="mt-6" leagueId={id} userTeamId={userTeam?.id} />
    </PageContainer>
  );
};
