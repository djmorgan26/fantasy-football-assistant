import React from 'react';
import { NewspaperIcon } from '@heroicons/react/24/outline';
import { Badge, Card, CardContent } from '@/components/ui';
import { PlayerIntel, TradePlayer } from '@/types';

const CATEGORY_VARIANT: Record<string, 'error' | 'warning' | 'default'> = {
  Injury: 'error',
  Transaction: 'warning',
  Rumor: 'default',
};

const when = (iso?: string | null): string | null => {
  if (!iso) return null;
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return null;
  const hours = Math.floor((Date.now() - then) / 3_600_000);
  if (hours < 1) return 'just now';
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return days === 1 ? 'yesterday' : `${days}d ago`;
};

/**
 * The context a projection cannot carry.
 *
 * Every line here is sourced: the depth-chart role and injury designation come
 * from the player index, the headlines from the news wire's own athlete tags.
 * Nothing is inferred, which is what makes it safe to put next to a number the
 * user is about to act on.
 */
export const PlayerNews: React.FC<{
  players: TradePlayer[];
  intel: Record<string, PlayerIntel>;
  title: string;
}> = ({ players, intel, title }) => {
  const entries = players
    .map((player) => ({ player, info: intel[player.player_id] }))
    .filter((row) => row.info);

  if (entries.length === 0) return null;

  const anythingToSay = entries.some(
    ({ info }) => info.role || info.injury || (info.headlines?.length ?? 0) > 0
  );
  if (!anythingToSay) return null;

  return (
    <Card>
      <CardContent className="space-y-4 pt-6">
        <h3 className="flex items-center gap-2 text-base font-semibold text-fg">
          <NewspaperIcon className="h-5 w-5 text-brand" aria-hidden="true" />
          {title}
        </h3>

        {entries.map(({ player, info }) => (
          <div key={player.player_id} className="border-b border-border pb-3 last:border-0 last:pb-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-medium text-fg">{info.full_name}</span>
              {info.nfl_team && (
                <span className="text-xs text-fg-muted">{info.nfl_team}</span>
              )}
              {info.role && (
                <Badge
                  variant={info.role.startsWith('Starting') ? 'success' : 'warning'}
                  size="sm"
                >
                  {info.role}
                </Badge>
              )}
              {info.injury && (
                <Badge variant="error" size="sm">
                  {info.injury.status}
                  {info.injury.body_part ? ` · ${info.injury.body_part}` : ''}
                </Badge>
              )}
              {typeof info.age === 'number' && (
                <span className="text-xs text-fg-muted">age {info.age}</span>
              )}
            </div>

            {info.injury?.practice && (
              <p className="mt-1 text-xs text-fg-muted">
                Practice: {info.injury.practice}
              </p>
            )}

            {info.headlines?.length > 0 && (
              <ul className="mt-2 space-y-1.5">
                {info.headlines.map((article, index) => (
                  <li key={`${article.headline}-${index}`} className="text-sm">
                    <div className="flex flex-wrap items-baseline gap-2">
                      {article.category && (
                        <Badge
                          variant={CATEGORY_VARIANT[article.category] ?? 'default'}
                          size="sm"
                          className="px-1.5 py-0 text-[10px]"
                        >
                          {article.category}
                        </Badge>
                      )}
                      {article.url ? (
                        <a
                          href={article.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-fg underline decoration-border underline-offset-2 hover:decoration-brand"
                        >
                          {article.headline}
                        </a>
                      ) : (
                        <span className="text-fg">{article.headline}</span>
                      )}
                      {when(article.published) && (
                        <span className="text-xs text-fg-muted">
                          {when(article.published)}
                        </span>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}
      </CardContent>
    </Card>
  );
};
