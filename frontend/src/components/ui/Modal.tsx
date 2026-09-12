import React, { Fragment } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { XMarkIcon } from '@heroicons/react/24/outline';
import { cn } from '@/utils';

type ModalSize = 'sm' | 'md' | 'lg' | 'xl';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: React.ReactNode;
  description?: React.ReactNode;
  children: React.ReactNode;
  footer?: React.ReactNode;
  size?: ModalSize;
  /** Hide the default close (X) button in the header. */
  hideClose?: boolean;
  className?: string;
}

const sizes: Record<ModalSize, string> = {
  sm: 'max-w-md',
  md: 'max-w-lg',
  lg: 'max-w-2xl',
  xl: 'max-w-4xl',
};

/**
 * Accessible modal built on Headless UI Dialog: focus trap, scroll lock,
 * Escape-to-close, and labelled title come for free.
 */
export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  description,
  children,
  footer,
  size = 'md',
  hideClose = false,
  className,
}) => {
  return (
    <Transition show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-200"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-150"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm" aria-hidden="true" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-y-auto">
          {/* Phones get a sheet anchored to the bottom edge, within thumb reach;
              from sm: up it is the usual centred dialog. */}
          <div className="flex min-h-full items-end justify-center p-0 sm:items-center sm:p-4">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-200"
              enterFrom="opacity-0 translate-y-4 sm:translate-y-2 sm:scale-95"
              enterTo="opacity-100 translate-y-0 sm:scale-100"
              leave="ease-in duration-150"
              leaveFrom="opacity-100 translate-y-0 sm:scale-100"
              leaveTo="opacity-0 translate-y-4 sm:translate-y-2 sm:scale-95"
            >
              <Dialog.Panel
                className={cn(
                  'flex max-h-[92vh] w-full flex-col rounded-t-card border border-border bg-surface-raised shadow-elevation-4 sm:max-h-[85vh] sm:rounded-card',
                  sizes[size],
                  className
                )}
              >
                {(title || !hideClose) && (
                  <div className="flex shrink-0 items-start justify-between gap-4 border-b border-border p-4 sm:p-5">
                    <div className="min-w-0">
                      {title && (
                        <Dialog.Title className="font-display text-lg font-bold text-fg">
                          {title}
                        </Dialog.Title>
                      )}
                      {description && (
                        <Dialog.Description className="mt-1 text-sm text-fg-muted">
                          {description}
                        </Dialog.Description>
                      )}
                    </div>
                    {!hideClose && (
                      <button
                        type="button"
                        onClick={onClose}
                        aria-label="Close dialog"
                        className="rounded-lg p-1 text-fg-subtle hover:bg-surface-sunken hover:text-fg focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      >
                        <XMarkIcon className="h-5 w-5" />
                      </button>
                    )}
                  </div>
                )}

                <div className="flex-1 overflow-y-auto p-4 sm:p-5">{children}</div>

                {footer && (
                  <div className="flex shrink-0 flex-col-reverse gap-3 border-t border-border p-4 pb-[calc(1rem+env(safe-area-inset-bottom,0px))] sm:flex-row sm:justify-end sm:p-5 sm:pb-5">
                    {footer}
                  </div>
                )}
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  );
};
