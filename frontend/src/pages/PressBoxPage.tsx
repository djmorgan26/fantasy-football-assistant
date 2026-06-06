import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useLeague } from '@/hooks/useLeagues';
import { useGenerateContent } from '@/hooks/useContent';
import { VoiceSettings } from '@/components/content/VoiceSettings';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { ContentType, GeneratedContent } from '@/types';
import { cn } from '@/utils';
import {
  ArrowLeftIcon,
  NewspaperIcon,
  TrophyIcon,
  SparklesIcon,
  ClipboardDocumentIcon,
  CheckIcon,
  Cog6ToothIcon,
  FireIcon,
} from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';

const CONTENT_OPTIONS: {
  type: ContentType;
  label: string;
  description: string;
  icon: React.ReactNode;
  needsWeek: boolean;
}[] = [
  {
    type: 'weekly_recap',
    label: 'Weekly Roast',
    description: 'A brutal, funny recap of the week',
    icon: <FireIcon className="h-5 w-5" />,
    needsWeek: true,
  },
  {
    type: 'power_rankings',
    label: 'Power Rankings',
    description: 'Every team ranked, with attitude',
    icon: <TrophyIcon className="h-5 w-5" />,
    needsWeek: true,
  },
  {
    type: 'awards',
    label: 'Weekly Awards',
    description: 'Funny superlatives from the week',
    icon: <SparklesIcon className="h-5 w-5" />,
    needsWeek: true,
  },
  {
    type: 'season_recap',
    label: 'Season Recap',
    description: 'Long-form season-in-review feature',
    icon: <NewspaperIcon className="h-5 w-5" />,
    needsWeek: false,
  },
];

export const PressBoxPage: React.FC = () => {
  const { leagueId } = useParams<{ leagueId: string }>();
  const navigate = useNavigate();
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
      <div className="container mx-auto px-4 py-8">
        <LoadingSpinner size="lg" className="mt-12" />
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-5xl">
      <Button variant="ghost" size="sm" onClick={() => navigate(`/leagues/${id}`)} className="mb-4">
        <ArrowLeftIcon className="h-4 w-4 mr-1" />
        Back to League
      </Button>

      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Press Box</h1>
          <p className="text-gray-600 mt-1">
            {league?.name} · AI content built from real weekly data + your league's voice
          </p>
        </div>
        <Button variant="secondary" size="sm" onClick={() => setShowSettings((v) => !v)}>
          <Cog6ToothIcon className="h-4 w-4 mr-1.5" />
          {showSettings ? 'Hide' : 'Voice'} Settings
        </Button>
      </div>

      {showSettings && (
        <div className="mb-8">
          <VoiceSettings leagueId={id} />
        </div>
      )}

      {/* Content type picker */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-5">
        {CONTENT_OPTIONS.map((opt) => (
          <button
            key={opt.type}
            onClick={() => setContentType(opt.type)}
            className={cn(
              'text-left p-4 rounded-lg border-2 transition-colors',
              contentType === opt.type
                ? 'border-primary-500 bg-primary-50'
                : 'border-gray-200 hover:border-gray-300'
            )}
          >
            <div
              className={cn(
                'mb-2',
                contentType === opt.type ? 'text-primary-600' : 'text-gray-400'
              )}
            >
              {opt.icon}
            </div>
            <div className="font-semibold text-gray-900 text-sm">{opt.label}</div>
            <div className="text-xs text-gray-500 mt-0.5">{opt.description}</div>
          </button>
        ))}
      </div>

      {/* Generate controls */}
      <Card className="mb-6">
        <div className="flex flex-wrap items-end gap-4">
          {selected.needsWeek && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Week</label>
              <input
                type="number"
                min={1}
                max={18}
                value={week}
                onChange={(e) => setWeek(parseInt(e.target.value, 10) || 1)}
                className="w-24 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
          )}
          <Button onClick={handleGenerate} loading={generate.isLoading}>
            <SparklesIcon className="h-4 w-4 mr-1.5" />
            Generate {selected.label}
          </Button>
        </div>
      </Card>

      {/* Result */}
      {generate.isLoading && (
        <div className="flex flex-col items-center py-12 text-gray-500">
          <LoadingSpinner size="lg" />
          <p className="mt-3 text-sm">Writing your {selected.label.toLowerCase()}...</p>
        </div>
      )}

      {result && !generate.isLoading && (
        <div className="space-y-5">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>{selected.label}</span>
                <div className="flex items-center gap-2">
                  <Badge variant={result.generated_by === 'fallback' ? 'warning' : 'success'} size="sm">
                    {result.generated_by === 'fallback' ? 'No AI key — facts only' : 'AI generated'}
                  </Badge>
                  <Button variant="ghost" size="sm" onClick={handleCopy}>
                    {copied ? (
                      <CheckIcon className="h-4 w-4 text-green-600" />
                    ) : (
                      <ClipboardDocumentIcon className="h-4 w-4" />
                    )}
                  </Button>
                </div>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="whitespace-pre-wrap text-gray-800 leading-relaxed">
                {result.content}
              </div>
            </CardContent>
          </Card>

          {result.narrative && <StoryFacts narrative={result.narrative} />}
        </div>
      )}
    </div>
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
            <div key={f.label} className="flex justify-between text-sm border-b border-gray-100 pb-1.5">
              <span className="text-gray-500">{f.label}</span>
              <span className="font-medium text-gray-900 text-right">{f.value}</span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};
