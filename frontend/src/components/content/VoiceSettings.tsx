import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { useContentProfile, useUpdateContentProfile } from '@/hooks/useContent';
import { HumorExample, ManagerPersona } from '@/types';
import { PlusIcon, TrashIcon } from '@heroicons/react/24/outline';

interface VoiceSettingsProps {
  leagueId: number;
}

const VOICE_PLACEHOLDER =
  "Describe how your league talks. e.g. 'Ruthless group chat energy. We never let anyone " +
  "live down a bad pick. Lots of nicknames, inside jokes about Dave's kicker obsession, and " +
  "trash talk that borders on personal. Funny first, accurate second.'";

export const VoiceSettings: React.FC<VoiceSettingsProps> = ({ leagueId }) => {
  const { data: profile, isLoading } = useContentProfile(leagueId);
  const updateProfile = useUpdateContentProfile(leagueId);

  const [voiceGuide, setVoiceGuide] = useState('');
  const [personas, setPersonas] = useState<ManagerPersona[]>([]);
  const [examples, setExamples] = useState<HumorExample[]>([]);

  useEffect(() => {
    if (profile) {
      setVoiceGuide(profile.voice_guide || '');
      setPersonas(profile.personas || []);
      setExamples(profile.humor_examples || []);
    }
  }, [profile]);

  const handleSave = () => {
    updateProfile.mutate({
      voice_guide: voiceGuide.trim() || null,
      personas: personas.filter((p) => p.name.trim()),
      humor_examples: examples.filter((e) => e.text.trim()),
    });
  };

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <LoadingSpinner size="md" />
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* Voice guide */}
      <Card>
        <CardHeader>
          <CardTitle>League Voice</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-500 mb-2">
            The tone the AI should write in. The more specific, the better it sounds like your group.
          </p>
          <textarea
            value={voiceGuide}
            onChange={(e) => setVoiceGuide(e.target.value)}
            rows={4}
            placeholder={VOICE_PLACEHOLDER}
            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </CardContent>
      </Card>

      {/* Manager personas */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>Manager Personas</span>
            <Button
              variant="secondary"
              size="sm"
              onClick={() =>
                setPersonas([...personas, { name: '', team_name: '', notes: '', bits: [] }])
              }
            >
              <PlusIcon className="h-4 w-4 mr-1" />
              Add
            </Button>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-500 mb-3">
            Who's in the league and what are their running jokes? Used to make callouts personal.
          </p>
          {personas.length === 0 && (
            <p className="text-sm text-gray-400">No personas yet.</p>
          )}
          <div className="space-y-4">
            {personas.map((p, i) => (
              <div key={i} className="p-3 border border-gray-200 rounded-lg space-y-2">
                <div className="flex gap-2">
                  <input
                    value={p.name}
                    onChange={(e) =>
                      setPersonas(personas.map((x, j) => (j === i ? { ...x, name: e.target.value } : x)))
                    }
                    placeholder="Name (e.g. Dave)"
                    className="flex-1 px-2 py-1.5 border border-gray-300 rounded text-sm"
                  />
                  <input
                    value={p.team_name || ''}
                    onChange={(e) =>
                      setPersonas(personas.map((x, j) => (j === i ? { ...x, team_name: e.target.value } : x)))
                    }
                    placeholder="Team name"
                    className="flex-1 px-2 py-1.5 border border-gray-300 rounded text-sm"
                  />
                  <button
                    onClick={() => setPersonas(personas.filter((_, j) => j !== i))}
                    className="text-gray-400 hover:text-red-500 px-1"
                    aria-label="Remove persona"
                  >
                    <TrashIcon className="h-4 w-4" />
                  </button>
                </div>
                <input
                  value={p.notes || ''}
                  onChange={(e) =>
                    setPersonas(personas.map((x, j) => (j === i ? { ...x, notes: e.target.value } : x)))
                  }
                  placeholder="Notes / personality (e.g. always benches his best player)"
                  className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm"
                />
                <input
                  value={p.bits.join(', ')}
                  onChange={(e) =>
                    setPersonas(
                      personas.map((x, j) =>
                        j === i
                          ? { ...x, bits: e.target.value.split(',').map((b) => b.trim()).filter(Boolean) }
                          : x
                      )
                    )
                  }
                  placeholder="Running bits, comma-separated (e.g. kicker truther, perennial choker)"
                  className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm"
                />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Past write-ups (the corpus) */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>Past Write-ups</span>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setExamples([...examples, { title: '', text: '' }])}
            >
              <PlusIcon className="h-4 w-4 mr-1" />
              Add
            </Button>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-500 mb-3">
            Paste previous years' reports here. The AI mimics this voice (it won't copy them).
            This is the single biggest lever on quality.
          </p>
          {examples.length === 0 && (
            <p className="text-sm text-gray-400">No examples yet — paste a few when you have them.</p>
          )}
          <div className="space-y-4">
            {examples.map((e, i) => (
              <div key={i} className="p-3 border border-gray-200 rounded-lg space-y-2">
                <div className="flex gap-2">
                  <input
                    value={e.title || ''}
                    onChange={(ev) =>
                      setExamples(examples.map((x, j) => (j === i ? { ...x, title: ev.target.value } : x)))
                    }
                    placeholder="Title (e.g. 2023 Championship Recap)"
                    className="flex-1 px-2 py-1.5 border border-gray-300 rounded text-sm"
                  />
                  <button
                    onClick={() => setExamples(examples.filter((_, j) => j !== i))}
                    className="text-gray-400 hover:text-red-500 px-1"
                    aria-label="Remove example"
                  >
                    <TrashIcon className="h-4 w-4" />
                  </button>
                </div>
                <textarea
                  value={e.text}
                  onChange={(ev) =>
                    setExamples(examples.map((x, j) => (j === i ? { ...x, text: ev.target.value } : x)))
                  }
                  rows={6}
                  placeholder="Paste the full write-up here..."
                  className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm"
                />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-end">
        <Button onClick={handleSave} loading={updateProfile.isLoading}>
          Save Voice Profile
        </Button>
      </div>
    </div>
  );
};
