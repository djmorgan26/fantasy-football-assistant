import React, { Fragment, useEffect, useRef, useState } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { useMatch } from 'react-router-dom';
import {
  PaperAirplaneIcon,
  SparklesIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';

import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { useCommissionerChat, usePromptSuggestions } from '@/hooks/useAssistant';
import { isRealLeagueId } from '@/components/layout/navConfig';
import { ChatTurn } from '@/types';
import { cn } from '@/utils';

/**
 * The Commissioner: a league-aware assistant, docked on every league page.
 *
 * It answers from the same grounded facts the content engine writes from —
 * standings, your roster, the week's results, live waiver trends — and in the
 * league's own voice rather than a product's. The chips are built from real
 * league state, because a generic "ask me anything" gets ignored and
 * "Should I start Reggie Petrov?" gets tapped.
 */
export const CommissionerDock: React.FC = () => {
  const match = useMatch('/leagues/:leagueId/*');
  const exact = useMatch('/leagues/:leagueId');
  const leagueId = match?.params?.leagueId ?? exact?.params?.leagueId;

  const [open, setOpen] = useState(false);
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [draft, setDraft] = useState('');
  const endRef = useRef<HTMLDivElement>(null);

  const id = parseInt(leagueId || '0', 10);
  const chat = useCommissionerChat(id);
  const { data: suggestions } = usePromptSuggestions(id, open && !!id);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [turns, chat.isLoading]);

  // Leaving one league for another should not carry the conversation over.
  useEffect(() => {
    setTurns([]);
  }, [leagueId]);

  if (!isRealLeagueId(leagueId)) return null;

  const ask = (message: string) => {
    const text = message.trim();
    if (!text || chat.isLoading) return;

    const history = turns;
    setTurns([...history, { role: 'user', content: text }]);
    setDraft('');

    chat.mutate(
      { message: text, history },
      {
        onSuccess: (reply) =>
          setTurns((prev) => [...prev, { role: 'assistant', content: reply.reply }]),
        onError: () =>
          setTurns((prev) => [
            ...prev,
            { role: 'assistant', content: "I couldn't get to that one. Try again in a second." },
          ]),
      }
    );
  };

  return (
    <>
      {/* A compact disc that clears the mobile tab bar and sits in the corner on
          desktop. It used to be a full pill with the label always showing,
          which floated a large opaque block over whatever was underneath it.
          The label now unfurls on hover or keyboard focus, so the resting
          footprint is one 48px target and the wording is still discoverable. */}
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label="Ask the Commissioner"
        className={cn(
          'group fixed right-4 z-30 flex h-12 items-center justify-center rounded-pill bg-brand px-3.5',
          'font-semibold text-brand-fg shadow-elevation-3',
          'transition-shadow hover:shadow-elevation-4 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
          'bottom-[calc(4.5rem+env(safe-area-inset-bottom,0px))] lg:bottom-6'
        )}
      >
        <SparklesIcon className="h-5 w-5 shrink-0" />
        <span
          className={cn(
            'max-w-0 overflow-hidden whitespace-nowrap text-sm opacity-0',
            'transition-all duration-200 motion-reduce:transition-none',
            'group-hover:ml-2 group-hover:max-w-[12rem] group-hover:opacity-100',
            'group-focus-visible:ml-2 group-focus-visible:max-w-[12rem] group-focus-visible:opacity-100'
          )}
        >
          Ask the Commissioner
        </span>
      </button>

      <Transition show={open} as={Fragment}>
        <Dialog as="div" className="relative z-50" onClose={setOpen}>
          <Transition.Child
            as={Fragment}
            enter="transition-opacity ease-linear duration-200"
            enterFrom="opacity-0"
            enterTo="opacity-100"
            leave="transition-opacity ease-linear duration-150"
            leaveFrom="opacity-100"
            leaveTo="opacity-0"
          >
            <div className="fixed inset-0 bg-black/50 backdrop-blur-sm" />
          </Transition.Child>

          <Transition.Child
            as={Fragment}
            enter="transition ease-in-out duration-250 transform"
            enterFrom="translate-y-full sm:translate-y-0 sm:translate-x-full"
            enterTo="translate-y-0 sm:translate-x-0"
            leave="transition ease-in-out duration-200 transform"
            leaveFrom="translate-y-0 sm:translate-x-0"
            leaveTo="translate-y-full sm:translate-y-0 sm:translate-x-full"
          >
            {/* A sheet on a phone, a side panel from sm: up. */}
            <Dialog.Panel className="fixed inset-x-0 bottom-0 flex h-[85vh] flex-col rounded-t-card border border-border bg-surface-raised shadow-elevation-4 sm:inset-y-0 sm:left-auto sm:right-0 sm:h-full sm:w-[26rem] sm:rounded-none sm:rounded-l-card">
              <div className="flex shrink-0 items-center justify-between gap-3 border-b border-border p-4">
                <div className="flex min-w-0 items-center gap-2">
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-brand/10">
                    <SparklesIcon className="h-4 w-4 text-brand" />
                  </span>
                  <div className="min-w-0">
                    <Dialog.Title className="font-display text-base font-bold text-fg">
                      The Commissioner
                    </Dialog.Title>
                    <p className="truncate text-xs text-fg-subtle">
                      Knows your whole league, not just your team
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setOpen(false)}
                  aria-label="Close"
                  className="rounded-lg p-1.5 text-fg-muted hover:bg-surface-sunken hover:text-fg focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <XMarkIcon className="h-5 w-5" />
                </button>
              </div>

              <div className="flex-1 overflow-y-auto p-4">
                {turns.length === 0 && (
                  <div className="flex flex-col gap-3">
                    <p className="text-sm text-fg-muted">
                      Ask about your lineup, a trade, the waiver wire, or why you lost.
                    </p>
                    {suggestions?.map((chip) => (
                      <button
                        key={chip}
                        type="button"
                        onClick={() => ask(chip)}
                        className="rounded-lg border border-border bg-surface px-3 py-2.5 text-left text-sm text-fg transition-colors hover:border-brand hover:bg-brand/5 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      >
                        {chip}
                      </button>
                    ))}
                  </div>
                )}

                <div className="flex flex-col gap-3">
                  {turns.map((turn, i) => (
                    <div
                      key={i}
                      className={cn(
                        'max-w-[85%] rounded-card px-3.5 py-2.5 text-sm leading-relaxed',
                        turn.role === 'user'
                          ? 'self-end bg-brand text-brand-fg'
                          : 'self-start bg-surface-sunken text-fg'
                      )}
                    >
                      <p className="whitespace-pre-wrap break-words">{turn.content}</p>
                    </div>
                  ))}

                  {chat.isLoading && (
                    <div className="self-start rounded-card bg-surface-sunken px-3.5 py-2.5">
                      <LoadingSpinner size="sm" />
                    </div>
                  )}
                </div>
                <div ref={endRef} />
              </div>

              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  ask(draft);
                }}
                className="flex shrink-0 gap-2 border-t border-border p-4 pb-[calc(1rem+env(safe-area-inset-bottom,0px))]"
              >
                <input
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  placeholder="Ask the Commissioner…"
                  aria-label="Your question"
                  className="min-h-[2.75rem] w-full rounded-lg border border-border bg-surface px-3 py-2 text-fg placeholder:text-fg-subtle focus:border-brand focus:outline-none focus-visible:ring-2 focus-visible:ring-ring/40 sm:text-sm"
                />
                <button
                  type="submit"
                  disabled={!draft.trim() || chat.isLoading}
                  aria-label="Send"
                  className="flex min-h-[2.75rem] w-11 shrink-0 items-center justify-center rounded-lg bg-brand text-brand-fg transition-opacity disabled:opacity-40 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <PaperAirplaneIcon className="h-5 w-5" />
                </button>
              </form>
            </Dialog.Panel>
          </Transition.Child>
        </Dialog>
      </Transition>
    </>
  );
};
