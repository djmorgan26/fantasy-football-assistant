import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { Input } from './Input';
import { Modal } from './Modal';
import { Select } from './Select';
import { Tabs } from './Tabs';
import { ToolHeader } from './ToolHeader';
import { EmptyState } from './EmptyState';
import { BeakerIcon } from '@heroicons/react/24/outline';

/**
 * The shared primitives. These are used on every page, so a regression here is
 * a regression everywhere — and they carry the mobile rules (touch targets,
 * scrollable tab strips, sheet-style modals) that are easy to undo by accident.
 */

describe('Input', () => {
  it('ties its label to the field so a click focuses it', async () => {
    render(<Input label="Week" />);
    const field = screen.getByLabelText('Week');

    await userEvent.click(screen.getByText('Week'));
    expect(field).toHaveFocus();
  });

  it('shows an error and marks the field invalid for assistive tech', () => {
    render(<Input label="Week" error="Pick a week between 1 and 18" />);
    expect(screen.getByText('Pick a week between 1 and 18')).toBeInTheDocument();
    expect(screen.getByLabelText('Week')).toHaveAttribute('aria-invalid', 'true');
  });

  it('is not marked invalid without an error', () => {
    render(<Input label="Week" />);
    expect(screen.getByLabelText('Week')).not.toHaveAttribute('aria-invalid');
  });
});

describe('Tabs', () => {
  const tabs = [
    { key: 'a', label: 'Newest' },
    { key: 'b', label: 'Top rated' },
  ];

  it('marks the active tab for assistive tech', () => {
    render(<Tabs tabs={tabs} value="a" onChange={() => {}} />);
    expect(screen.getByRole('tab', { name: 'Newest' })).toHaveAttribute(
      'aria-selected',
      'true'
    );
  });

  it('reports the tab that was clicked', async () => {
    const onChange = vi.fn();
    render(<Tabs tabs={tabs} value="a" onChange={onChange} />);

    await userEvent.click(screen.getByRole('tab', { name: 'Top rated' }));
    expect(onChange).toHaveBeenCalledWith('b');
  });

  it('moves between tabs with the arrow keys', async () => {
    const onChange = vi.fn();
    render(<Tabs tabs={tabs} value="a" onChange={onChange} />);

    screen.getByRole('tab', { name: 'Newest' }).focus();
    await userEvent.keyboard('{ArrowRight}');
    expect(onChange).toHaveBeenCalledWith('b');
  });

  it('wraps around at the end', async () => {
    const onChange = vi.fn();
    render(<Tabs tabs={tabs} value="b" onChange={onChange} />);

    screen.getByRole('tab', { name: 'Top rated' }).focus();
    await userEvent.keyboard('{ArrowRight}');
    expect(onChange).toHaveBeenCalledWith('a');
  });

  it('keeps only the active tab in the tab order', () => {
    // Roving focus: Tab enters the strip once, arrows move within it.
    render(<Tabs tabs={tabs} value="a" onChange={() => {}} />);
    expect(screen.getByRole('tab', { name: 'Newest' })).toHaveAttribute('tabindex', '0');
    expect(screen.getByRole('tab', { name: 'Top rated' })).toHaveAttribute('tabindex', '-1');
  });

  it('scrolls rather than clipping when the tabs do not fit', () => {
    const { container } = render(<Tabs tabs={tabs} value="a" onChange={() => {}} />);
    // A clipped fourth tab was unreachable on a phone before this.
    expect(container.querySelector('[role="tablist"]')?.className).toContain('rail');
  });
});

describe('Modal', () => {
  it('stays out of the DOM when closed', () => {
    render(
      <Modal isOpen={false} onClose={() => {}} title="Select Your Team">
        <p>body</p>
      </Modal>
    );
    expect(screen.queryByText('Select Your Team')).toBeNull();
  });

  it('shows its title, description and children when open', async () => {
    render(
      <Modal isOpen onClose={() => {}} title="Select Your Team" description="Pick yours.">
        <p>body</p>
      </Modal>
    );

    expect(await screen.findByText('Select Your Team')).toBeInTheDocument();
    expect(screen.getByText('Pick yours.')).toBeInTheDocument();
    expect(screen.getByText('body')).toBeInTheDocument();
  });

  it('closes from the X', async () => {
    const onClose = vi.fn();
    render(
      <Modal isOpen onClose={onClose} title="Select Your Team">
        <p>body</p>
      </Modal>
    );

    await userEvent.click(await screen.findByRole('button', { name: 'Close dialog' }));
    expect(onClose).toHaveBeenCalled();
  });

  it('can hide the close button for a forced choice', async () => {
    render(
      <Modal isOpen onClose={() => {}} title="Select Your Team" hideClose>
        <p>body</p>
      </Modal>
    );
    await screen.findByText('Select Your Team');
    expect(screen.queryByRole('button', { name: 'Close dialog' })).toBeNull();
  });

  it('renders footer actions', async () => {
    render(
      <Modal isOpen onClose={() => {}} title="Disconnect" footer={<button>Confirm</button>}>
        <p>Sure?</p>
      </Modal>
    );
    expect(await screen.findByRole('button', { name: 'Confirm' })).toBeInTheDocument();
  });
});

describe('Select', () => {
  const options = [
    { value: '1', label: 'Week 1' },
    { value: '2', label: 'Week 2' },
  ];

  it('shows the selected option', () => {
    render(<Select value="2" onChange={() => {}} options={options} />);
    expect(screen.getByRole('button')).toHaveTextContent('Week 2');
  });

  it('shows a placeholder when nothing matches', () => {
    render(
      <Select value="" onChange={() => {}} options={options} placeholder="Pick a week" />
    );
    expect(screen.getByRole('button')).toHaveTextContent('Pick a week');
  });

  it('reports the chosen value', async () => {
    const onChange = vi.fn();
    render(<Select value="1" onChange={onChange} options={options} />);

    await userEvent.click(screen.getByRole('button'));
    await userEvent.click(await screen.findByRole('option', { name: 'Week 2' }));

    expect(onChange).toHaveBeenCalledWith('2');
  });

  it('does not open when disabled', async () => {
    render(<Select value="1" onChange={() => {}} options={options} disabled />);
    await userEvent.click(screen.getByRole('button'));
    expect(screen.queryByRole('option')).toBeNull();
  });
});

describe('ToolHeader', () => {
  it('states the tool and the context it is showing', () => {
    render(<ToolHeader title="Starting Lineup" context="Week 14" />);
    expect(screen.getByText('Starting Lineup')).toBeInTheDocument();
    expect(screen.getByText('Week 14')).toBeInTheDocument();
  });

  it('carries its controls', () => {
    render(<ToolHeader title="League Wire" actions={<button>Summarize</button>} />);
    expect(screen.getByRole('button', { name: 'Summarize' })).toBeInTheDocument();
  });

  it('works without an icon, subtitle or actions', () => {
    render(<ToolHeader title="Draft Room" />);
    expect(screen.getByRole('heading', { name: 'Draft Room' })).toBeInTheDocument();
  });
});

describe('EmptyState', () => {
  it('explains the situation and offers a way out', () => {
    render(
      <EmptyState
        icon={BeakerIcon}
        title="Nothing on the board yet"
        description="Post the first thing."
        action={<button>Write a post</button>}
      />
    );

    expect(screen.getByText('Nothing on the board yet')).toBeInTheDocument();
    expect(screen.getByText('Post the first thing.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Write a post' })).toBeInTheDocument();
  });

  it('works with only a title', () => {
    render(<EmptyState icon={BeakerIcon} title="No teams found" />);
    expect(screen.getByText('No teams found')).toBeInTheDocument();
  });
});
