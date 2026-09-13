# Design

The **Stadium** system: semantic tokens that flip between light and dark, plus
the mobile rules the layout depends on.

Colours are stored in `src/index.css` as space-separated RGB channels so
Tailwind's `rgb(var(--x) / <alpha-value>)` opacity modifiers keep working
(`bg-surface/50`). The `.dark` class on `<html>` swaps the variables; every
component reads tokens, never literals.

Never hardcode a Tailwind grey. A colour whose only definition works in one
theme is the classic unreadable-in-dark-mode bug.

## Token mapping

## Color mapping (apply everywhere)
| Old (hardcoded) | New (semantic token) |
| --- | --- |
| `bg-white` | `bg-surface-raised` |
| `bg-gray-50` | `bg-surface` (or drop — shell provides it) |
| `bg-gray-100` | `bg-surface-sunken` |
| `bg-gray-200` (wells/tracks) | `bg-surface-sunken` or `bg-border` |
| `text-gray-900` / `text-black` | `text-fg` |
| `text-gray-800` / `text-gray-700` | `text-fg` |
| `text-gray-600` / `text-gray-500` | `text-fg-muted` |
| `text-gray-400` | `text-fg-subtle` |
| `border-gray-200` / `border-gray-300` | `border-border` |
| `divide-gray-200` | `divide-border` |
| `hover:bg-gray-50` / `hover:bg-gray-100` | `hover:bg-surface-sunken` |
| `text-primary-600` (links/accents) | `text-brand` |
| `bg-primary-600` (solid) | `bg-brand text-brand-fg` (prefer `<Button>`) |
| `ring-primary-*` (focus) | `focus-visible:ring-ring` |

## Keep as-is (work in both themes)
- `success-*`, `warning-*`, `error-*` ramps for status text/badges (e.g. `text-error-600`, `text-success-600`).
- `getPositionColor()` from `@/utils` (already dark-aware) — never inline position colors.

## Primitives to reuse (from `@/components/ui`)
`Button`, `Card`/`CardHeader`/`CardTitle`/`CardContent`, `Badge`, `Input`, `Select`, `Modal`,
`Tabs`, `Progress`, `Skeleton`/`SkeletonCard`/`SkeletonGrid`, `EmptyState`, `Tooltip`, `LoadingSpinner`/`LoadingPage`.
- Loading: prefer `Skeleton*` for page/section loads; `LoadingSpinner` for inline.
- Empty / error / no-results: use `<EmptyState icon=… title=… description=… action=… variant="error"? />`.
- Dialogs: use `<Modal>` (focus trap + scroll lock + Escape), never raw `fixed inset-0`.

## Typography
- `h1`–`h6` already default to the Bricolage display font via base CSS — no class needed.
- Use `font-display` on non-heading elements that should look like headlines (big stat numbers).
- Add `tabular` (font-variant-numeric: tabular-nums) to scores/standings/PF-PA numbers.

## a11y
- Icon-only buttons need `aria-label`.
- Dynamic regions (live draft picks, regenerated suggestions, search results, trade analysis) wrap in `aria-live="polite"`.
- Use `focus-visible:ring-2 focus-visible:ring-ring` for keyboard focus.

## Type

| Role | Face | Used for |
| --- | --- | --- |
| Display | Bricolage Grotesque | headings, scores, stat tiles |
| Body | Plus Jakarta Sans | everything else |

Display sizes (`text-display-lg`, `text-display`, `text-display-sm`) are
`clamp()`-based, so a long league name arrives on a phone at phone size instead
of wrapping to four lines.

## Mobile rules

These are load-bearing — the layout was rebuilt around them and they are easy
to undo by accident:

- **Touch targets.** Buttons, inputs and selects get 44px minimum height below `sm:` only; desktop keeps its tighter rhythm.
- **16px fields on phones.** iOS zooms the page whenever a focused input is under 16px. `index.css` enforces this below `sm:`.
- **Tab strips scroll.** The `.rail` utility gives horizontal scroll with no visible scrollbar. A clipped fourth tab is unreachable, not just ugly.
- **Modals are sheets.** Bottom-anchored below `sm:`, centred above it, with their own scroll region and safe-area padding.
- **Safe areas.** `pb-safe`, `px-safe` and `pb-tabbar` keep content clear of the notch, the home indicator and the fixed bottom nav.
- **Cards tighten.** 16px padding on phones, 24px from `sm:` up.

## Layout shell

- **Desktop**: collapsible left sidebar owns navigation.
- **Phone and tablet**: a fixed bottom tab bar carries the current league's first four sections plus **More**, which opens the full drawer. The bar is `lg:hidden`; the sidebar is `lg:flex`.
- `PageContainer` and `PageHeader` (`components/layout/Page.tsx`) decide gutters, max width and the title/actions stacking rule once, for every page.

## The dark band

`ToolHeader` renders a saturated `#16221C` band naming the tool and the context
it is showing ("Starting Lineup — Week 14 — ppr scoring"), with the controls
that change that context inside it. Light, dense content sits below. The
figure/ground split does most of the orienting work on a page that is otherwise
a stack of similar cards.
