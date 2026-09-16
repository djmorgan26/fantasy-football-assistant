import React from 'react';
import {
  ArrowDownIcon,
  ArrowUpIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  MinusCircleIcon,
  SparklesIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline';
import { Badge, Card, CardContent, CardHeader, CardTitle, Progress } from '@/components/ui';
import { PositionDepth, TradeEvaluation, TradeVerdict } from '@/types';
import { cn } from '@/utils';

const VERDICT_STYLES: Record<
  TradeVerdict,
  { label: string; icon: React.ComponentType<React.SVGProps<SVGSVGElement>>; tone: string; ring: string }
> = {
  accept: {
    label: 'Accept',
    icon: CheckCircleIcon,
    tone: 'text-success-600 dark:text-success-400',
    ring: 'bg-success-100 dark:bg-success-900/40',
  },
  lean_accept: {
    label: 'Lean accept',
    icon: ArrowUpIcon,
    tone: 'text-success-600 dark:text-success-400',
    ring: 'bg-success-100 dark:bg-success-900/40',
  },
  neutral: {
    label: 'Toss-up',
    icon: MinusCircleIcon,
    tone: 'text-fg-muted',
    ring: 'bg-surface-sunken',
  },
  lean_reject: {
    label: 'Lean reject',
    icon: ArrowDownIcon,
    tone: 'text-warning-600 dark:text-warning-400',
    ring: 'bg-warning-100 dark:bg-warning-900/40',
  },
  reject: {
    label: 'Reject',
    icon: XCircleIcon,
    tone: 'text-error-600 dark:text-error-400',
    ring: 'bg-error-100 dark:bg-error-900/40',
  },
};

const signed = (n: number, digits = 1) => `${n >= 0 ? '+' : ''}${n.toFixed(digits)}`;

const deltaTone = (n: number) =>
  n > 0.05
    ? 'text-success-600 dark:text-success-400'
    : n < -0.05
    ? 'text-error-600 dark:text-error-400'
    : 'text-fg-muted';

/**
 * The answer to "should I do this", in the order a manager actually decides.
 *
 * Playoff odds lead because they are the only figure that folds together
 * points, schedule and the rest of the league. Weekly lineup change comes next
 * as the concrete version of the same thing, then fairness, which says whether
 * the *other* manager should say yes. The AI paragraph is last on purpose: it
 * explains numbers that are already on screen rather than supplying them.
 */
export const TradeVerdictPanel: React.FC<{ evaluation: TradeEvaluation }> = ({
  evaluation,
}) => {
  const style = VERDICT_STYLES[evaluation.verdict] ?? VERDICT_STYLES.neutral;
  const Icon = style.icon;
  const odds = evaluation.playoff_odds;

  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-start gap-4">
            <div className={cn('rounded-full p-3', style.ring)}>
              <Icon className={cn('h-7 w-7', style.tone)} aria-hidden="true" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <h3 className={cn('text-xl font-bold', style.tone)}>{style.label}</h3>
                <Badge variant="default" size="sm">
                  Fairness {evaluation.fairness_score.toFixed(0)}/100
                </Badge>
              </div>
              <p className="mt-1 text-sm text-fg-muted">{evaluation.headline}</p>
            </div>
          </div>

          <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Stat
              label="Playoff odds"
              value={
                odds ? `${odds.before.toFixed(0)}% → ${odds.after.toFixed(0)}%` : 'Not simulated'
              }
              delta={odds ? signed(odds.delta) : undefined}
              tone={odds ? deltaTone(odds.delta) : undefined}
              hint={
                odds
                  ? `${odds.iterations.toLocaleString()} simulations of the remaining ${odds.weeks_simulated} week${
                      odds.weeks_simulated === 1 ? '' : 's'
                    }, top ${odds.playoff_spots} make it`
                  : 'No regular season games left to simulate'
              }
            />
            <Stat
              label="Your starting lineup"
              value={`${evaluation.you.lineup_before.toFixed(1)} → ${evaluation.you.lineup_after.toFixed(1)}`}
              delta={signed(evaluation.you.lineup_delta)}
              tone={deltaTone(evaluation.you.lineup_delta)}
              hint="Projected points per week, best legal lineup"
            />
          </div>

          <div className="mt-6">
            <div className="mb-2 flex items-center justify-between">
              <span className="text-sm font-medium text-fg">Value split</span>
              <span className="text-xs text-fg-muted">
                {evaluation.fairness_score >= 85
                  ? 'Balanced'
                  : evaluation.you.value_in > evaluation.them.value_in
                  ? 'Favours you'
                  : 'Favours them'}
              </span>
            </div>
            <ValueSplit
              yours={evaluation.you.value_in}
              theirs={evaluation.them.value_in}
              yourName="You get"
              theirName="They get"
            />
          </div>
        </CardContent>
      </Card>

      {evaluation.risks.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <ExclamationTriangleIcon className="h-5 w-5 text-warning-600" aria-hidden="true" />
              Watch out
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {evaluation.risks.map((risk) => (
                <li key={risk} className="flex items-start gap-2 text-sm text-fg-muted">
                  <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-warning-500" />
                  {risk}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      <DepthTable evaluation={evaluation} />

      {(evaluation.ai_summary || evaluation.ai_points.length > 0) && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <SparklesIcon className="h-5 w-5 text-brand" aria-hidden="true" />
              The read
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {evaluation.ai_summary && (
              <p className="text-sm leading-relaxed text-fg">{evaluation.ai_summary}</p>
            )}
            {evaluation.ai_points.length > 0 && (
              <ul className="space-y-1.5">
                {evaluation.ai_points.map((point) => (
                  <li key={point} className="flex items-start gap-2 text-sm text-fg-muted">
                    <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-brand" />
                    {point}
                  </li>
                ))}
              </ul>
            )}
            {evaluation.counter_suggestion && (
              <div className="rounded-lg border border-border bg-surface-sunken p-3">
                <p className="text-xs font-semibold uppercase tracking-wide text-fg-muted">
                  Counter
                </p>
                <p className="mt-1 text-sm text-fg">{evaluation.counter_suggestion}</p>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
};

const Stat: React.FC<{
  label: string;
  value: string;
  delta?: string;
  tone?: string;
  hint: string;
}> = ({ label, value, delta, tone, hint }) => (
  <div className="rounded-lg border border-border bg-surface-sunken p-4">
    <p className="text-xs font-semibold uppercase tracking-wide text-fg-muted">{label}</p>
    <div className="mt-1 flex items-baseline gap-2">
      <span className="tabular text-lg font-bold text-fg">{value}</span>
      {delta && <span className={cn('tabular text-sm font-semibold', tone)}>{delta}</span>}
    </div>
    <p className="mt-1 text-xs text-fg-muted">{hint}</p>
  </div>
);

/**
 * One bar split by who gets more value, rather than two bars to compare by eye.
 * The whole question is the ratio, so the ratio is what gets drawn.
 */
const ValueSplit: React.FC<{
  yours: number;
  theirs: number;
  yourName: string;
  theirName: string;
}> = ({ yours, theirs, yourName, theirName }) => {
  const total = yours + theirs;
  const share = total > 0 ? (yours / total) * 100 : 50;
  return (
    <>
      <Progress
        value={share}
        label="Share of trade value you receive"
        barClassName={share >= 45 ? 'bg-success-500' : 'bg-warning-500'}
      />
      <div className="mt-1.5 flex justify-between text-xs text-fg-muted">
        <span className="tabular">
          {yourName} {yours.toFixed(1)}
        </span>
        <span className="tabular">
          {theirName} {theirs.toFixed(1)}
        </span>
      </div>
    </>
  );
};

/** Only the positions the trade actually moves. A full grid is mostly zeroes. */
const DepthTable: React.FC<{ evaluation: TradeEvaluation }> = ({ evaluation }) => {
  const { depth_before: before, depth_after: after } = evaluation.you;
  const changed = Object.keys(after).filter((position) => {
    const b: PositionDepth | undefined = before[position];
    const a = after[position];
    return b && a && (b.startable !== a.startable || b.rostered !== a.rostered);
  });

  if (changed.length === 0) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Roster shape after the trade</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-fg-muted">
                <th className="pb-2 pr-4 font-semibold">Position</th>
                <th className="pb-2 pr-4 font-semibold">Startable</th>
                <th className="pb-2 font-semibold">Need</th>
              </tr>
            </thead>
            <tbody>
              {changed.map((position) => {
                const b = before[position];
                const a = after[position];
                const short = a.startable < a.required;
                return (
                  <tr key={position} className="border-b border-border last:border-0">
                    <td className="py-2 pr-4 font-medium text-fg">{position}</td>
                    <td className="tabular py-2 pr-4 text-fg-muted">
                      {b.startable} → <span className={short ? 'text-error-600' : 'text-fg'}>{a.startable}</span>
                    </td>
                    <td className="tabular py-2 text-fg-muted">{a.required}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-xs text-fg-muted">
          "Startable" counts players projected above a freely available starter at that
          position in this league.
        </p>
      </CardContent>
    </Card>
  );
};
