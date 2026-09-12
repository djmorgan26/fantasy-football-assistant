import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useLeague } from '@/hooks/useLeagues';
import { useGenerateContent } from '@/hooks/useContent';
import { VoiceSettings } from '@/components/content/VoiceSettings';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Input } from '@/components/ui/Input';
import { Tabs } from '@/components/ui/Tabs';
import { SkeletonCard } from '@/components/ui/Skeleton';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { ContentType, GeneratedContent } from '@/types';
import {
  NewspaperIcon,
  TrophyIcon,
  SparklesIcon,
  ClipboardDocumentIcon,
  CheckIcon,
  Cog6ToothIcon,
  FireIcon,
} from '@heroicons/react/24/outline';
import { PageContainer, PageHeader } from '@/components/layout/Page';
import toast from 'react-hot-toast';

const CONTENT_OPTIONS: {
  type: ContentType;
  label: string;
  description: string;
  icon: React.ComponentType<React.SVGProps<SVGSVGElement>>;
  needsWeek: boolean;
}[] = [
  {
    type: 'weekly_recap',
    label: 'Weekly Roast',
    description: 'A brutal, funny recap of the week',
    icon: FireIcon,
    needsWeek: true,
  },
  {
    type: 'power_rankings',
    label: 'Power Rankings',
    description: 'Every team ranked, with attitude',
    icon: TrophyIcon,
    needsWeek: true,
  },
  {
    type: 'awards',
    label: 'Weekly Awards',
    description: 'Funny superlatives from the week',
    icon: SparklesIcon,
    needsWeek: true,
  },
  {
    type: 'season_recap',
    label: 'Season Recap',
    description: 'Long-form season-in-review feature',
    icon: NewspaperIcon,
    needsWeek: false,
  },
];

export const PressBoxPage: React.FC = () => {
  const { leagueId } = useParams<{ leagueId: string }>();
  const id = parseInt(leagueId || '0', 10);
  const { data: league, isLoading } = useLeague(id);
  const generate = useGenerateContent(id);

  const [contentType, setContentType] = useState<ContentType>('weekly_recap');
  const [week, setWeek] = useState<number>(Math.max((league?.current_week || 1) - 1, 1));
  const [result, setResult] = useState<GeneratedContent | null>(null);
  const [copied, setCopied] = useState(false);
  const [showSettings, setShowSettings] = useState(false);

  const selected = CONTENT_OPTIONS.find((o) => o.type === contentType)!;

  const handleGenerate = async () => {
    setResult(null);
    const res = await generate.mutateAsync({
      contentType,
      week: selected.needsWeek ? week : undefined,
    });
    setResult(res);
  };

  const handleCopy = async () => {
    if (!result) return;
    await navigator.clipboard.writeText(result.content);
    setCopied(true);
    toast.success('Copied to clipboard');
    setTimeout(() => setCopied(false), 2000);
  };

  if (isLoading) {
    return (
      <PageContainer>
        <div className="space-y-5">
          <SkeletonCard />
          <SkeletonCard />
        </div>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <PageHeader
        backTo={`/leagues/${id}`}
        backLabel="Back to League"
        title="Press Box"
        subtitle={`${league?.name ?? ''} · AI content built from real weekly data + your league's voice`}
        actions={
          <Button variant="secondary" size="sm" onClick={() => setShowSettings((v) => !v)}>
            <Cog6ToothIcon className="h-4 w-4" />
            {showSettings ? 'Hide settings' : 'Voice settings'}
          </Button>
        }
      />

      {showSettings && (
        <div className="mb-8">
          <VoiceSettings leagueId={id} />
        </div>
      )}

      {/* Content type picker */}
      <div className="mb-5">
        <Tabs
          aria-label="Content type"
          value={contentType}
          onChange={(key) => setContentType(key as ContentType)}
          tabs={CONTENT_OPTIONS.map((opt) => ({
            key: opt.type,
            label: opt.label,
            icon: opt.icon,
          }))}
        />
        <p className="text-sm text-fg-muted mt-2">{selected.description}</p>
      </div>

      {/* Generate controls */}
      <Card className="mb-6">
        <div className="flex flex-wrap items-end gap-3 sm:gap-4">
          {selected.needsWeek && (
            <Input
              label="Week"
              type="number"
              inputMode="numeric"
              min={1}
              max={18}
              value={week}
              onChange={(e) => setWeek(parseInt(e.target.value, 10) || 1)}
              className="w-20"
            />
          )}
          <Button
            onClick={handleGenerate}
            loading={generate.isLoading}
            className="w-full sm:w-auto"
          >
            <SparklesIcon className="h-4 w-4" />
            Generate {selected.label}
          </Button>
        </div>
      </Card>

      {/* Result */}
      <div aria-live="polite">
        {generate.isLoading && (
          <div className="space-y-5">
            <div className="flex flex-col items-center py-6 text-fg-muted">
              <LoadingSpinner size="lg" />
              <p className="mt-3 text-sm">Writing your {selected.label.toLowerCase()}...</p>
            </div>
            <SkeletonCard />
          </div>
        )}

        {result && !generate.isLoading && (
          <div className="space-y-5">
            <Card>
              <CardHeader>
                <CardTitle className="flex flex-wrap items-center justify-between gap-2">
                  <span>{selected.label}</span>
                  <div className="flex items-center gap-2">
                    <Badge variant={result.generated_by === 'fallback' ? 'warning' : 'success'} size="sm">
                      {result.generated_by === 'fallback' ? 'No AI key — facts only' : 'AI generated'}
                    </Badge>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleCopy}
                      aria-label={copied ? 'Copied to clipboard' : 'Copy to clipboard'}
                    >
                      {copied ? (
                        <CheckIcon className="h-4 w-4 text-success-600" />
                      ) : (
                        <ClipboardDocumentIcon className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="whitespace-pre-wrap break-words text-fg leading-relaxed">
                  {result.content}
                </div>
              </CardContent>
            </Card>

            {result.narrative && <StoryFacts narrative={result.narrative} />}
          </div>
        )}
      </div>
    </PageContainer>
  );
};

const StoryFacts: React.FC<{ narrative: NonNullable<GeneratedContent['narrative']> }> = ({
  narrative,
}) => {
  const facts: { label: string; value: string }[] = [];
  if (narrative.highest_scorer)
    facts.push({
      label: 'Top scorer',
      value: `${narrative.highest_scorer.team_name} (${narrative.highest_scorer.points})`,
    });
  if (narrative.lowest_scorer)
    facts.push({
      label: 'Low scorer',
      value: `${narrative.lowest_scorer.team_name} (${narrative.lowest_scorer.points})`,
    });
  if (narrative.biggest_blowout)
    facts.push({
      label: 'Biggest blowout',
      value: `${narrative.biggest_blowout.winner} by ${narrative.biggest_blowout.margin}`,
    });
  if (narrative.closest_game)
    facts.push({
      label: 'Closest game',
      value: `${narrative.closest_game.winner} by ${narrative.closest_game.margin}`,
    });
  if (narrative.bench_blunder)
    facts.push({
      label: 'Bench blunder',
      value: `${narrative.bench_blunder.team_name} left ${narrative.bench_blunder.bench_points} on the bench`,
    });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Story facts used</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {facts.map((f) => (
            <div
              key={f.label}
              className="flex flex-col gap-0.5 border-b border-border pb-1.5 text-sm sm:flex-row sm:justify-between sm:gap-4"
            >
              <span className="text-fg-muted">{f.label}</span>
              <span className="font-medium text-fg sm:text-right">{f.value}</span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};
