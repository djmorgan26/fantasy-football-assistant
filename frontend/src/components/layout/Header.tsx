import React, { Fragment } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/Button';
import { ThemeToggle } from '@/components/ui/ThemeToggle';
import {
  UserCircleIcon,
  ChevronDownIcon,
  Cog6ToothIcon,
  ArrowRightOnRectangleIcon,
} from '@heroicons/react/24/outline';
import { Menu, Transition } from '@headlessui/react';
import { cn } from '@/utils';

/**
 * Sticky top bar: brand (mobile only, the sidebar carries it on desktop),
 * theme toggle and the user menu. Navigation lives in the sidebar on desktop
 * and in the bottom tab bar on phones, so there is no menu button here.
 */
export const Header: React.FC = () => {
  const { user, isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <header className="sticky top-0 z-30 border-b border-border bg-surface/80 backdrop-blur-md">
      <div className="flex h-14 items-center justify-between gap-3 px-4 sm:h-16 sm:px-6">
        <div className="flex min-w-0 items-center gap-3">
          {/* Brand — visible on mobile (sidebar shows it on desktop) */}
          <Link to="/" className="flex min-w-0 items-center gap-2 lg:hidden">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-brand">
              <span className="text-sm font-bold text-brand-fg">FF</span>
            </div>
            <span className="truncate font-display text-base font-bold text-fg sm:text-lg">
              Fantasy Football
            </span>
          </Link>
        </div>

        <div className="flex shrink-0 items-center gap-1 sm:gap-2">
          <ThemeToggle />

          {isAuthenticated ? (
            <Menu as="div" className="relative">
              <Menu.Button className="flex min-h-[2.5rem] items-center gap-2 rounded-lg px-2 py-1.5 text-fg-muted transition-colors hover:bg-surface-sunken hover:text-fg focus:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                <UserCircleIcon className="h-6 w-6" />
                <span className="hidden max-w-[12rem] truncate text-sm font-medium sm:inline">
                  {user?.full_name || user?.email}
                </span>
                <ChevronDownIcon className="h-4 w-4" />
              </Menu.Button>

              <Transition
                as={Fragment}
                enter="transition ease-out duration-100"
                enterFrom="transform opacity-0 scale-95"
                enterTo="transform opacity-100 scale-100"
                leave="transition ease-in duration-75"
                leaveFrom="transform opacity-100 scale-100"
                leaveTo="transform opacity-0 scale-95"
              >
                <Menu.Items className="absolute right-0 mt-2 w-48 overflow-hidden rounded-lg border border-border bg-surface-raised shadow-elevation-3 focus:outline-none">
                  <div className="py-1">
                    <Menu.Item>
                      {({ active }) => (
                        <Link
                          to="/profile"
                          className={cn(
                            'flex min-h-[2.75rem] items-center px-4 py-2 text-sm',
                            active ? 'bg-surface-sunken text-fg' : 'text-fg-muted'
                          )}
                        >
                          <Cog6ToothIcon className="mr-2 h-4 w-4" />
                          Profile Settings
                        </Link>
                      )}
                    </Menu.Item>
                    <Menu.Item>
                      {({ active }) => (
                        <button
                          onClick={handleLogout}
                          className={cn(
                            'flex min-h-[2.75rem] w-full items-center px-4 py-2 text-left text-sm',
                            active ? 'bg-surface-sunken text-fg' : 'text-fg-muted'
                          )}
                        >
                          <ArrowRightOnRectangleIcon className="mr-2 h-4 w-4" />
                          Sign Out
                        </button>
                      )}
                    </Menu.Item>
                  </div>
                </Menu.Items>
              </Transition>
            </Menu>
          ) : (
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" onClick={() => navigate('/login')}>
                Sign In
              </Button>
              <Button size="sm" onClick={() => navigate('/register')}>
                Sign Up
              </Button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
