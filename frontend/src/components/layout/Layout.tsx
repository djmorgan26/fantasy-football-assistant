import React, { Fragment, useState } from 'react';
import { Outlet, Link, useMatch } from 'react-router-dom';
import { Dialog, Transition } from '@headlessui/react';
import { XMarkIcon } from '@heroicons/react/24/outline';
import { Header } from './Header';
import { SidebarNav } from './SidebarNav';
import { AppToaster } from '@/components/ui/AppToaster';

interface LayoutProps {
  children?: React.ReactNode;
}

const Brand: React.FC = () => (
  <Link to="/" className="flex items-center gap-2">
    <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand">
      <span className="text-sm font-bold text-brand-fg">FF</span>
    </div>
    <span className="font-display text-lg font-bold leading-tight text-fg">Fantasy&nbsp;Football</span>
  </Link>
);

export const Layout: React.FC<LayoutProps> = ({ children }) => {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const match = useMatch('/leagues/:leagueId/*');
  const leagueId = match?.params?.leagueId;

  return (
    <div className="min-h-screen bg-surface text-fg">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-[60] focus:rounded-lg focus:bg-brand focus:px-4 focus:py-2 focus:text-brand-fg"
      >
        Skip to content
      </a>

      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col border-r border-border bg-surface-raised lg:flex">
        <div className="flex h-16 items-center border-b border-border px-5">
          <Brand />
        </div>
        <div className="flex-1 overflow-y-auto p-4">
          <SidebarNav leagueId={leagueId} />
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
      <div className="lg:pl-64">
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
