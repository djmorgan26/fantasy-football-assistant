import React from 'react';
import { ArrowTopRightOnSquareIcon } from '@heroicons/react/24/outline';

import { Badge } from '@/components/ui/Badge';
import { NewsArticle } from '@/types';
import { cn, formatDate } from '@/utils';

const CATEGORY_TONE: Record<string, 'error' | 'warning' | 'secondary' | 'default'> = {
  Injury: 'error',
  Transaction: 'secondary',
  Rumor: 'warning',
  Recap: 'default',
};

/**
 * One item off the wire.
 *
 * The structure is lifted from how the big fantasy sites write player updates:
 * headline, source, then a clearly separated "what this means" line. Raw wire
 * copy is a commodity; the translation is the product. Ours has an advantage
 * they cannot copy — we know which team in *this* league rosters the player,
 * so the impact line can name whose problem it is.
 */
export const NewsCard: React.FC<{ article: NewsArticle }> = ({ article }) => {
  const tone = CATEGORY_TONE[article.category] ?? 'default';

  return (
    <article
      className={cn(
        'rounded-card border bg-surface-raised p-4 transition-shadow hover:shadow-elevation-2',
        article.rostered_by ? 'border-brand/40 border-l-4 border-l-brand' : 'border-border'
      )}
    >
      <div className="flex gap-4">
        {article.image && (
          <img
            src={article.image}
            alt=""
            loading="lazy"
            className="hidden h-20 w-28 shrink-0 rounded-lg object-cover sm:block"
          />
        )}

        <div className="min-w-0 flex-1">
          <div className="mb-1.5 flex flex-wrap items-center gap-2">
            <Badge variant={tone} size="sm">
              {article.category}
            </Badge>
            {article.rostered_by && (
              <span className="rounded-pill bg-brand/10 px-2 py-0.5 text-xs font-semibold text-brand">
                {article.rostered_by}
              </span>
            )}
            {article.published && (
              <span className="text-xs text-fg-subtle">{formatDate(article.published)}</span>
            )}
          </div>

          <h3 className="font-display text-base font-bold leading-snug text-fg">
            {article.headline}
          </h3>

          {article.description && (
            <p className="mt-1.5 text-sm leading-relaxed text-fg-muted">{article.description}</p>
          )}

          <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-fg-subtle">
            {article.byline && <span>{article.byline}</span>}
            {article.teams.length > 0 && <span>{article.teams.join(' · ')}</span>}
            {article.url && (
              <a
                href={article.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 font-semibold text-brand hover:underline"
              >
                Read
                <ArrowTopRightOnSquareIcon className="h-3 w-3" />
              </a>
            )}
          </div>
        </div>
      </div>
    </article>
  );
};
