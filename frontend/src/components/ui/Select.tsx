import { Fragment } from 'react';
import { Listbox, Transition } from '@headlessui/react';
import { CheckIcon, ChevronDownIcon } from '@heroicons/react/24/outline';
import { cn } from '@/utils';

export interface SelectOption<T extends string = string> {
  value: T;
  label: string;
}

interface SelectProps<T extends string = string> {
  value: T;
  onChange: (value: T) => void;
  options: SelectOption<T>[];
  label?: string;
  placeholder?: string;
  fullWidth?: boolean;
  className?: string;
  disabled?: boolean;
  size?: 'sm' | 'md';
}

/** Styled, accessible select built on Headless UI Listbox to match Input. */
export function Select<T extends string = string>({
  value,
  onChange,
  options,
  label,
  placeholder = 'Select…',
  fullWidth = false,
  className,
  disabled,
  size = 'md',
}: SelectProps<T>) {
  const selected = options.find((o) => o.value === value);

  const buttonSizes = {
    sm: 'py-1.5 pl-3 pr-8 text-sm',
    md: 'py-2 pl-3 pr-10 text-sm',
  };

  return (
    <div className={cn('flex flex-col', fullWidth && 'w-full', className)}>
      {label && <label className="mb-1 block text-sm font-medium text-fg">{label}</label>}
      <Listbox value={value} onChange={onChange} disabled={disabled}>
        {({ open }) => (
          <div className="relative">
            <Listbox.Button
              className={cn(
                'relative w-full cursor-pointer rounded-lg border border-border bg-surface-raised text-left text-fg shadow-sm transition-colors',
                'hover:border-border-strong',
                'focus:outline-none focus-visible:border-brand focus-visible:ring-2 focus-visible:ring-ring/40',
                'disabled:cursor-not-allowed disabled:opacity-50',
                open && 'border-brand ring-2 ring-ring/40',
                buttonSizes[size]
              )}
            >
              <span className={cn('block truncate', !selected && 'text-fg-subtle')}>
                {selected ? selected.label : placeholder}
              </span>
              <span
                className={cn(
                  'pointer-events-none absolute inset-y-0 right-0 flex items-center',
                  size === 'sm' ? 'pr-2' : 'pr-2.5'
                )}
              >
                <ChevronDownIcon
                  className={cn(
                    'h-4 w-4 text-fg-subtle transition-transform duration-150',
                    open && 'rotate-180 text-brand'
                  )}
                  aria-hidden="true"
                />
              </span>
            </Listbox.Button>
            <Transition
              as={Fragment}
              enter="transition ease-out duration-150"
              enterFrom="opacity-0 -translate-y-1 scale-[0.98]"
              enterTo="opacity-100 translate-y-0 scale-100"
              leave="transition ease-in duration-100"
              leaveFrom="opacity-100"
              leaveTo="opacity-0"
            >
              <Listbox.Options className="absolute z-50 mt-1.5 max-h-60 w-max min-w-full overflow-auto rounded-lg border border-border bg-surface-raised py-1 text-sm shadow-elevation-3 focus:outline-none">
                {options.map((opt) => (
                  <Listbox.Option
                    key={opt.value}
                    value={opt.value}
                    className={({ active }) =>
                      cn(
                        'relative cursor-pointer select-none py-2 pl-9 pr-4 transition-colors',
                        active ? 'bg-brand/10 text-fg' : 'text-fg-muted'
                      )
                    }
                  >
                    {({ selected: isSel }) => (
                      <>
                        <span className={cn('block truncate', isSel && 'font-semibold text-fg')}>
                          {opt.label}
                        </span>
                        {isSel && (
                          <span className="absolute inset-y-0 left-0 flex items-center pl-2.5 text-brand">
                            <CheckIcon className="h-4 w-4" aria-hidden="true" />
                          </span>
                        )}
                      </>
                    )}
                  </Listbox.Option>
                ))}
              </Listbox.Options>
            </Transition>
          </div>
        )}
      </Listbox>
    </div>
  );
}
