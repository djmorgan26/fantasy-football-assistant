import React, { Fragment, useState } from 'react';
import { Outlet, Link, useMatch } from 'react-router-dom';
import { Dialog, Transition } from '@headlessui/react';
import {
  XMarkIcon,
  ChevronDoubleLeftIcon,
  ChevronDoubleRightIcon,
} from '@heroicons/react/24/outline';
import { Header } from './Header';
import { SidebarNav } from './SidebarNav';
import { AppToaster } from '@/components/ui/AppToaster';
import { cn } from '@/utils';

interface LayoutProps {
  children?: React.ReactNode;
}

const SIDEBAR_COLLAPSED_KEY = 'ff:sidebar-collapsed';

const Brand: React.FC<{ compact?: boolean }> = ({ compact = false }) => (
  <Link to="/" className="flex items-center gap-2" aria-label="Fantasy Football home">
    <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-brand">
      <span className="text-sm font-bold text-brand-fg">FF</span>
    </div>
    {!compact && (
      <span className="font-display text-lg font-bold leading-tight text-fg">Fantasy&nbsp;Football</span>
    )}
  </Link>
);

export const Layout: React.FC<LayoutProps> = ({ children }) => {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(
    () => localStorage.getItem(SIDEBAR_COLLAPSED_KEY) !== '0'
  );
  const match = useMatch('/leagues/:leagueId/*');
  const leagueId = match?.params?.leagueId;

  const toggleCollapsed = () => {
    setCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem(SIDEBAR_COLLAPSED_KEY, next ? '1' : '0');
      return next;
    });
  };

  return (
    <div className="min-h-screen bg-surface text-fg">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-[60] focus:rounded-lg focus:bg-brand focus:px-4 focus:py-2 focus:text-brand-fg"
      >
        Skip to content
      </a>

      {/* Desktop sidebar */}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-30 hidden flex-col border-r border-border bg-surface-raised transition-[width] duration-200 lg:flex',
          collapsed ? 'w-[4.5rem]' : 'w-64'
        )}
      >
        <div
          className={cn(
            'flex h-16 items-center border-b border-border',
            collapsed ? 'justify-center px-2' : 'px-5'
          )}
        >
          <Brand compact={collapsed} />
        </div>
        <div className={cn('flex-1 overflow-y-auto', collapsed ? 'p-3' : 'p-4')}>
          <SidebarNav leagueId={leagueId} collapsed={collapsed} />
        </div>
        <div className={cn('border-t border-border', collapsed ? 'p-3' : 'p-4')}>
          <button
            type="button"
            onClick={toggleCollapsed}
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            className={cn(
              'flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-semibold text-fg-muted transition-colors hover:bg-surface-sunken hover:text-fg focus:outline-none focus-visible:ring-2 focus-visible:ring-ring',
              collapsed && 'justify-center px-2'
            )}
          >
            {collapsed ? (
              <ChevronDoubleRightIcon className="h-5 w-5 flex-shrink-0 text-fg-subtle" />
            ) : (
              <>
                <ChevronDoubleLeftIcon className="h-5 w-5 flex-shrink-0 text-fg-subtle" />
                Collapse
              </>
            )}
          </button>
        </div>
      </aside>

      {/* Mobile drawer */}
      <Transition show={drawerOpen} as={Fragment}>
        <Dialog as="div" className="relative z-40 lg:hidden" onClose={setDrawerOpen}>
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
            enter="transition ease-in-out duration-200 transform"
            enterFrom="-translate-x-full"
            enterTo="translate-x-0"
            leave="transition ease-in-out duration-150 transform"
            leaveFrom="translate-x-0"
            leaveTo="-translate-x-full"
          >
            <Dialog.Panel className="fixed inset-y-0 left-0 flex w-72 flex-col bg-surface-raised shadow-elevation-4">
              <div className="flex h-16 items-center justify-between border-b border-border px-5">
                <Brand />
                <button
                  type="button"
                  onClick={() => setDrawerOpen(false)}
                  aria-label="Close navigation menu"
                  className="rounded-lg p-1.5 text-fg-muted hover:bg-surface-sunken hover:text-fg focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <XMarkIcon className="h-6 w-6" />
                </button>
              </div>
              <div className="flex-1 overflow-y-auto p-4">
                <SidebarNav leagueId={leagueId} onNavigate={() => setDrawerOpen(false)} />
              </div>
            </Dialog.Panel>
          </Transition.Child>
        </Dialog>
      </Transition>

      {/* Main column */}
      <div
        className={cn(
          'transition-[padding] duration-200',
          collapsed ? 'lg:pl-[4.5rem]' : 'lg:pl-64'
        )}
      >
        <Header onMenuToggle={() => setDrawerOpen(true)} />
        <main id="main" className="flex-1">
          {children || <Outlet />}
        </main>
      </div>

      <AppToaster position="top-right" />
    </div>
  );
};

export const AuthLayout: React.FC<LayoutProps> = ({ children }) => {
  return (
    <div className="flex min-h-screen flex-col justify-center bg-surface py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="flex justify-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-brand">
            <span className="text-xl font-bold text-brand-fg">FF</span>
          </div>
        </div>
        <h2 className="mt-6 text-center font-display text-3xl font-bold tracking-tight text-fg">
          Fantasy Football Assistant
        </h2>
      </div>

      <div className="mt-8">{children || <Outlet />}</div>

      <AppToaster position="top-center" />
    </div>
  );
};
