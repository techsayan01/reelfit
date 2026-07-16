# Reelfit visual redesign — “Cinematic dark studio”

Status: **approved direction, not yet implemented.** This doc is the pick-up
point for the redesign. The current UI (warm palette, top tab-nav, centered
column, right sidebar, card grid) reads too close to FilmFreeway; this redesign
changes both the **visual identity** and the **structural organization** so it
stops looking like a clone.

**Visual reference:** open [redesign/dark-studio-mockup.html](redesign/dark-studio-mockup.html)
in a browser — a before/after of the festival dashboard plus the palette swatches.

---

## The direction in one line

A dark, screening-room console with a **left sidebar app-shell**, poster/
thumbnail-forward rows, and a single restrained accent — a purpose-built
festival tool, not a submissions marketplace.

## Design tokens

Introduce these as CSS custom properties in `frontend/src/styles.css` (`:root`),
replacing the current warm light theme. Keep names semantic so components never
hardcode hex.

| Token | Value | Role |
|---|---|---|
| `--ink` | `#0E0E10` | Page canvas |
| `--panel` | `#151517` | Sidebar, raised panels |
| `--tile` | `#18181B` | Metric tiles, list rows |
| `--line` | `#26262B` | Hairline borders |
| `--swatch` | `#2A2A2E` | Poster/thumbnail placeholder |
| `--paper` | `#F5F2EC` | Primary text |
| `--muted` | `#9A968E` | Secondary text |
| `--dim` | `#7E7A72` | Tertiary text, captions |
| `--amber` | `#E8B23A` | **Single accent** — Marquee Amber, brightened for dark. Primary buttons, active nav, key status. |
| `--teal` | `#5DCAA5` | Success / “selected” status only |
| `--red` | `#E2635C` | Errors / rejected only |

Accent discipline: **one amber-filled action per view.** Everything else is
neutral. Teal/red are reserved for status meaning, never decoration.

## Typography

- Keep a **display serif for headings** (it's a genuine brand asset and works on
  dark) but pair it with a crisper body sans and tighten sizes so it stops
  echoing FilmFreeway's proportions.
- Numbers / tracking numbers / IDs → monospace (`--font-mono`), tabular.
- Sentence case everywhere. No ALL-CAPS section headers.

## Structural change — the biggest tell

Replace the **top tab-bar + centered narrow column** with a **left sidebar app
shell** for signed-in users:

```
┌────────────┬─────────────────────────────────────┐
│  Reelfit   │  Hillside Film Festival   [Review ▸] │
│  ▸ Submis. │  ┌─────┐ ┌─────┐ ┌─────┐             │
│    Judging │  │  2  │ │  1  │ │$122 │  metric row │
│    Staff   │  └─────┘ └─────┘ └─────┘             │
│    Analyt. │  ▸ Glass Houses      HIL1002  In rev. │
│    Settings│  ▸ Monsoon Letters   HIL1001  Select. │
│  ──────────│                                       │
│  Arjun M.  │                                       │
└────────────┴─────────────────────────────────────┘
```

- **Festival side:** sidebar = Submissions · Judging · Staff · Analytics ·
  Settings. Content area is full-width (no more squeezed 3fr/2fr with the
  submissions table overflowing — see the container-query fix already landed).
- **Filmmaker side:** sidebar = My films · Submissions · Credits · Profile.
- **Public/marketing pages** (home, festival directory, public filmmaker
  profile) keep a **top nav**, not the sidebar — they're for logged-out
  visitors. Only the authenticated app gets the shell.
- Mobile: sidebar collapses to a bottom bar or a drawer behind the existing
  hamburger.

## Component mapping (what changes, file by file)

| Area | Now | After |
|---|---|---|
| `components/Layout.jsx` | top nav for everyone | split: `AppShell` (sidebar) for authed app, `TopNav` for public pages |
| `styles.css` `:root` | warm light tokens | dark tokens above; keep a light theme only for public marketing pages if desired |
| `.card` | white card, warm border | `--tile`/`--panel` surfaces, `--line` borders |
| `.two-col` (dashboards) | 3fr/2fr squeeze | full-width content; secondary info in a right rail only where it helps |
| Submissions manager | stacked `.stack` table | poster-forward rows (thumbnail · title · meta · status chip) |
| Status tags | amber/teal pills | keep, retuned for dark (`--bg` darker, text lighter) |
| Fit Score dial (`ScoreDial`) | signature element | keep — glows well on dark; make it the hero of the film/scores view |

## Phased rollout

1. **Tokens + one page.** Add dark tokens; rebuild the **festival dashboard**
   end-to-end (sidebar shell + full-width content + poster rows). Get sign-off.
2. **App shell everywhere authed.** Filmmaker dashboard, film scores, submit,
   credits, profile editor, festival submission detail — all move into the shell.
3. **Public pages.** Restyle home, festival directory/detail, public filmmaker
   profile to the dark identity (keeping top nav).
4. **Polish.** Empty states, focus rings, motion, dark-tuned status colors,
   mobile sidebar/drawer, accessibility contrast pass (WCAG AA on `--paper`/
   `--muted` over `--ink`/`--tile`).

Structure the theme as a **design-token layer + shared `AppShell` component** so
it's consistent and reversible, rather than per-page hex edits.

## Decisions log

- **2026-07-16** — Direction chosen: dark-studio with left sidebar (over
  editorial-minimal and warm-new-structure options). Approved from the
  before/after mockup.

## Open questions (decide before Phase 1)

- Do the **public/marketing pages** go dark too, or stay light for a brighter
  first impression? (Current plan: dark identity, top nav.)
- Keep the **display serif** headings, or switch to an all-sans grotesk for a
  cleaner break from the current look?
- Sidebar **iconography**: Tabler outline set (used in the mockup) or a custom
  film-motif set?
