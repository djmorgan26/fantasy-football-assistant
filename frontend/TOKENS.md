# Stadium token migration guide (internal)

Replace hardcoded Tailwind grays/whites with semantic tokens so light + dark both work.
The `.dark` class on `<html>` flips the CSS variables; tokens handle the rest.

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
