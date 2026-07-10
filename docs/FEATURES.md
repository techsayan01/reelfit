# Reelfit Feature Reference

This is the complete, code-accurate reference for what Reelfit's Phase 1
structured monolith does today. It's organized by area, cross-referenced to
the BRD, and includes every API endpoint, data model, and frontend page.
Where a feature deliberately differs from incumbent platforms (e.g.
FilmFreeway), that's called out — Reelfit's differentiators aren't
accidents.

For setup and quick start, see [../README.md](../README.md). For a running
list of what's intentionally out of scope for Phase 1, see
[Deferred & rejected](#deferred--rejected-items).

## Contents

- [Filmmaker features](#filmmaker-features)
- [Festival features](#festival-features)
- [Cross-cutting systems](#cross-cutting-systems)
- [Data model](#data-model)
- [API reference](#api-reference)
- [Frontend routes](#frontend-routes)
- [Design system](#design-system)
- [Demo data](#demo-data)
- [Deferred & rejected items](#deferred--rejected-items)

---

## Filmmaker features

### Account & film library (BRD §5.2.1)
- Register as a filmmaker; first account gets **1 free scoring credit**.
- Film/project library: add finished films *or* screenplays (`kind`:
  `film` | `screenplay`). Screenplays skip runtime entirely — the scoring
  engine treats runtime as neutral for them, and festival categories can be
  restricted to one project kind.
- Each project carries: title, genre, runtime, year, country, language,
  logline, synopsis, freeform credits (`Name — Role` per line), screener
  and trailer URLs (YouTube/Vimeo), first-time-filmmaker and
  student-project flags.
- **Masked contact relay**: festivals never see a filmmaker's real email.
  Every submission gets a unique relay handle (`relay-xxxxx`); filmmakers
  can revoke a festival's access at any time with no support ticket.

### Fit scoring (★ BRD §5.2.2 — differentiator)
- **One flat credit scores a film against every listed festival at once** —
  not a fee per festival compared.
- The engine ([app/modules/scoring/engine.py](../app/modules/scoring/engine.py))
  scores 0–100 from three signals: genre affinity relative to the
  festival's own historical acceptance rate, runtime closeness to that
  festival's selected median, and recency of selections in that genre.
- Every score carries a **calibration status** — `validated` once a
  festival has ≥30 confirmed historical selection outcomes, `calibrating`
  before that. The label is shown next to every score, everywhere, so no
  score is ever presented as more certain than the data supports (BRD
  §7.5).
- Screenplays score with the runtime component held neutral.

### Submission workflow (BRD §5.2.2–5.2.3)
- Multi-step submit flow: category (auto-filtered to eligible categories
  by runtime/production-year/project-kind rules), current deadline tier
  fee, promo code entry, **custom submission form** questions (see
  below), optional cover letter.
- **Discount, fee-waiver, and deadline-waiver codes** apply at checkout;
  the fee shown updates live.
- **Late entries**: once a festival's final deadline passes, submitting
  is only possible with a valid deadline-waiver code, inside the
  festival's configured waiver window, at the final tier's fee.
- Every submission gets a sequential **tracking number** (e.g.
  `HIL1001`) scoped to the festival.
- A confirmation step is required before any paid or costly action —
  scoring, submitting, revoking contact — per the BRD's "never punish
  exploration" design principle.

### Tracking & outcomes (BRD §5.2.3)
- Dashboard shows every submission across every festival, current status,
  fee paid, and notifications in one place.
- Judging status lifecycle: `received → in_review → shortlisted →
  finalist → selected / award_winner / honorable_mention → rejected`.
  The three "made it in" statuses all count toward selection stats and
  unlock a certificate.
- Status changes always generate an automatic notification — filmmakers
  are never left guessing.

### Post-festival (BRD §5.2.4)
- **Laurel/certificate download** once selected — rendered as SVG on
  demand, styled to the festival's branding.
- **Verified reviews**: only filmmakers with a real, confirmed submission
  to a festival may review it, one review per submission. Festivals get
  a public right-of-reply. This is the direct answer to the BRD's
  critique of unmoderated review systems (§5.3, §9).
- **Distribution guidance**: rule-based, plain-language recommendations
  (aggregator / TVOD / AVOD-FAST / self-distribution) based on genre,
  runtime, and festival-selection count. Reelfit never takes rights,
  never acts as a sales agent — this module only recommends (BRD §3.2,
  §9).

### Payments (BRD §5.2.5)
- Scoring credit packs (single / 3-pack / 5-pack) purchased through a
  dev-mode payment provider today; production swaps in Stripe behind the
  same `payments/service.py` interface with no caller changes.
- Full payment and credit-ledger history per user.

---

## Festival features

### Organization & staff (BRD §5.1.1)
- Multiple staff accounts per festival organization with roles: `owner`,
  `programmer`, `jury`, `viewer`. Owners add staff by email (must already
  have a Reelfit account) and can remove anyone but themselves.
- Multi-edition support: each festival can run distinct yearly cycles
  with their own dates, categories, and fee tiers.
- Every sensitive action is guarded **both** in the UI (cards/controls
  hidden) and in the API (403 on direct calls) — verified for staff
  management, status changes, and rubric edits.

### Submission configuration (BRD §5.1.2)
- Categories with runtime rules, production-year minimums, and a
  `kind` (film or screenplay) — screenplay categories skip runtime
  checks entirely.
- Deadline tiers (early bird / regular / late / …) with fee deltas
  applied to each category's base fee.
- **Discounts & waivers**: three code types —
  - `discount` — percent or flat amount off
  - `fee_waiver` — free entry
  - `deadline_waiver` — entry allowed past the final deadline
  - Discount codes can *also* function as deadline waivers.
  - Codes support an internal label, category scoping, date windows,
    unlimited or capped total uses, and **one-use-per-submitter**
    enforcement via a redemption ledger.
- **Deadline waiver period**: a per-festival number of days past the
  final deadline during which waiver codes still work; the UI shows the
  computed "accepted through" date live as it's edited.
- **Custom submission form**: owners define extra questions (single-line
  text, paragraph, dropdown with options, yes/no) required for all
  categories or one specific category. Submissions are rejected
  server-side if a required question goes unanswered or a dropdown
  answer doesn't match a configured option.

### Review & judging (BRD §5.1.3)
- **Scoring rubric**: owner-configured criteria with weights; a one-click
  "standard film judging form" seeds the nine default criteria
  (Originality/Creativity, Direction, Writing, Cinematography,
  Performances, Production Value, Pacing, Structure, Sound/Music).
- **Judge assignment**: assign/unassign staff to a submission; each
  festival member sees a personal **review queue** of pending
  assignments that clears automatically once they score an entry.
- **Rating**: judges score 1–10 per criterion, leave a free-form comment,
  and pick an overall recommendation (`pass` / `maybe` / `recommend` /
  `award_worthy`). A submission's rating is the average of each judge's
  own weighted score, averaged again across judges.
- **Judging Insights**: totals (judged / not judged / % judged) plus a
  per-judge table — assigned count, judged count, % judged, and total
  runtime assigned.
- **Internal notes**: jury-only notes on a submission, never visible to
  the filmmaker.
- **Status audit log**: every judging-status change records who changed
  it, from what, to what, and when.
- **Custom flags**: owner-defined colored labels (9-color palette) to
  organize submissions; shown as color dots in the submissions list with
  a dedicated filter.

### Filmmaker communication (BRD §5.1.4)
- Automatic notifications on submission-received and every status
  change.
- **Bulk messaging** ("Email Submitters" / "Email Judges & Staff"): send
  to all current submitters or all staff at once, with a confirmation
  step and a sent-message history log. Explicitly not for selection
  results — those are automatic.
- **Webhooks**: register a URL to receive `submission.received` and
  `submission.status_changed` events as POSTed JSON. Delivery is
  attempted immediately in a background thread with a delivery log
  (✓/✗ and status code) visible per endpoint; production moves this to a
  retrying Celery task without changing the public interface.

### Analytics & dashboards (★ BRD §5.1.5 — differentiator)
- **Submission volume dashboard**: totals, breakdown by judging status,
  gross revenue, discount usage — the "This cycle" card.
- **Marketing / conversion analytics**: every public festival-page view
  is logged with its traffic source (`?ref=` query param, shareable via
  a one-click "copy link" per source). The dashboard shows
  views → submissions → conversion % → fees, per source — computed from
  real platform records, **never self-reported** (contrast with
  incumbents' unverifiable "estimated submissions" marketing stats).
- **Transactions**: a monthly fee ledger with expandable per-submission
  detail.
- **Reports**: downloadable CSV aggregates — sales by category, by
  judging status, by month, by traffic source.
- **Export configurations**: owners save named sets of columns (from 16
  available) for repeatable spreadsheet exports; a full-column export is
  always available. Contact columns always use the masked relay address
  — filmmaker PII never leaves through an export (BRD §7.5).

### Financial (BRD §5.1.6)
- Submission fee collection net of discounts/waivers, recorded per
  submission.
- Credit-pack and festival-licensing payment types modeled in the
  payments ledger (licensing invoicing is a Phase 2 UI item).

### Branding & public listing (BRD §5.1.7)
- Public profile: logo/cover image URLs, description, rules, awards &
  prizes text, contact email/phone/website/social links, venue
  name/address, founded year.
- **Calibration badge**: "Validated scoring" / "Scoring calibrating" tag
  shown everywhere the festival appears — the honest alternative to
  purchased trust badges.
- **Public stats** on the listing page (years running, total
  submissions, selected count, average review rating) — computed from
  real records, never self-reported.
- **Non-public listing toggle** (`is_public`): hide a festival from
  search and direct access while its profile is still being set up.
- **Reviews visibility toggle**: show or hide filmmaker reviews on the
  public listing page independent of collecting them internally.
- **Deadline timeline**: opening date, every fee tier, and notification
  date shown on the public page with the current tier highlighted.
- **Laurel Center**: configurable laurel graphic (text + black/white
  variant) with a live preview against a matching background, a
  downloadable SVG, and a copyable public link for laurel recipients —
  no login required to fetch it.
- **Ad Creator**: headline/subline/CTA/background social-graphic
  generator in Reelfit's palette, rendered live as SVG, downloadable in
  Instagram-square and Facebook/X-wide formats.

---

## Cross-cutting systems

- **Session-cookie auth** ([app/api/deps.py](../app/api/deps.py)): no
  JWTs or API keys exposed to end users, per the BRD's non-technical-user
  requirement. Role dependencies (`FilmmakerDep`, `OrganizerDep`) gate
  every route.
- **Masked contact relay**: implemented once in `submissions` and reused
  everywhere a festival needs to reach a filmmaker (notifications,
  dashboard contact column, exports).
- **Help Center**: plain-language FAQ page (`/help`) covering general,
  filmmaker, and festival questions, in the same voice as the rest of
  the product.
- **Module boundaries**: every `app/modules/<name>/service.py` is the
  only way other modules may touch that module's data — no cross-module
  SQL joins. This is what keeps "structured monolith" honest and
  decomposable later (BRD §7.1, §7.3).

---

## Data model

One entry per SQLAlchemy model class, grouped by owning module. See each
module's `models.py` for full field lists.

| Module | Models |
|---|---|
| `accounts` | `User`, `FestivalMembership`, `Film` |
| `festivals` | `Festival`, `FestivalEdition`, `Category`, `DeadlineTier`, `CustomQuestion`, `FlagDef`, `TrackingVisit`, `HistoricalSelection` |
| `discounts` | `DiscountCode`, `CodeRedemption`, `FeeWaiver` |
| `jury` | `RubricCriterion`, `JuryAssignment`, `JuryScore`, `InternalNote` |
| `submissions` | `Submission`, `ExportConfig`, `CustomAnswer`, `StatusChange` |
| `scoring` | `FitScore` |
| `reviews` | `Review` |
| `payments` | `PaymentRecord`, `CreditLedgerEntry` |
| `certificates` | `Certificate` |
| `notifications` | `Notification`, `BulkMessage`, `WebhookEndpoint`, `WebhookDelivery` |

`recommendations` and `dashboards` are compute-only modules with no
persisted models — they read through other modules' services.

---

## API reference

All routes are session-authenticated JSON under `/api`. Interactive docs
at `/internal/docs` when the server is running.

### Auth — `/api/auth`
| Method | Path | Purpose |
|---|---|---|
| POST | `/register` | Create an account (filmmaker or organizer) |
| POST | `/login` | Session login |
| POST | `/logout` | Clear session |
| GET | `/me` | Current user, or `null` |

### Public festivals — `/api/festivals`
| Method | Path | Purpose |
|---|---|---|
| GET | `` | List public festivals (search, region filter) |
| GET | `/{slug}` | Festival detail: profile, categories, timeline, stats, reviews. Logs a tracking visit via `?ref=` |
| GET | `/{slug}/laurel.svg` | Public laurel graphic, no auth |

### Films — `/api/films` (filmmaker)
| Method | Path | Purpose |
|---|---|---|
| GET | `` | List my films |
| POST | `` | Add a film or screenplay |
| POST | `/{id}/score` | Score against every listed festival (spends 1 credit) |
| GET | `/{id}/scores` | Latest scores + distribution guidance |

### Submissions — `/api/submissions` (filmmaker)
| Method | Path | Purpose |
|---|---|---|
| GET | `` | My submissions + notifications |
| GET | `/options` | Eligible categories/fees/custom questions for a film × festival |
| POST | `` | Submit (discount code, cover letter, custom answers, source) |
| POST | `/{id}/revoke-relay` | Revoke a festival's contact access |
| GET | `/{id}/certificate.svg` | Laurel download (selected/award/honorable-mention only) |

### Reviews — `/api/reviews` (filmmaker)
| Method | Path | Purpose |
|---|---|---|
| POST | `` | Review a festival (submission-verified) |

### Credits — `/api/credits` (filmmaker)
| Method | Path | Purpose |
|---|---|---|
| GET | `/packs` | Available credit packs |
| POST | `/buy` | Purchase a pack |

### Festival admin — `/api/festival` (organizer)
| Method | Path | Purpose |
|---|---|---|
| GET | `/dashboard` | Submissions, overview, reviews, flags, statuses |
| PATCH | `/profile` | Edit public profile (owner only) |
| GET/POST | `/staff` | List / add staff (owner only for POST) |
| DELETE | `/staff/{id}` | Remove staff (owner only) |
| GET/POST | `/rubric` | List / add rubric criteria (owner only for POST) |
| DELETE | `/rubric/{id}` | Delete a criterion (owner only) |
| POST | `/rubric/defaults` | Seed the standard film judging form (owner only) |
| GET/POST | `/questions` | Custom submission-form questions (owner only for POST) |
| DELETE | `/questions/{id}` | Delete a question (owner only) |
| GET/POST | `/flags` | Custom flags (owner only for POST) |
| DELETE | `/flags/{id}` | Delete a flag (owner only) |
| GET | `/queue` | My review queue |
| GET | `/submissions/{id}` | Full submission detail: film, filmmaker, judges, rubric, log, notes, custom answers |
| POST | `/submissions/{id}/assign` / `/unassign` | Judge assignment (programmer/owner) |
| POST | `/submissions/{id}/rate` | Submit rubric scores + comment + recommendation |
| POST | `/submissions/{id}/flag` | Set/clear a submission's flag |
| POST | `/submissions/{id}/notes` | Add an internal (jury-only) note |
| POST | `/submissions/{id}/status` | Change judging status (programmer/owner) — notifies filmmaker, fires webhook |
| POST | `/reviews/{id}/reply` | Public right-of-reply to a review |
| GET/POST | `/messages` | Bulk-message history / send (programmer/owner) |
| GET | `/insights` | Per-judge judging progress |
| GET | `/marketing` | Conversion analytics by traffic source |
| GET | `/transactions` | Monthly fee ledger |
| GET | `/reports` | Aggregate CSV report |
| GET/POST | `/export-configs` | Saved export column sets (owner only for POST) |
| DELETE | `/export-configs/{id}` | Delete a config (owner only) |
| GET | `/export` | Submission CSV export (`?config_id=`) |
| GET/POST | `/webhooks` | List / register webhooks (owner only for POST) |
| DELETE | `/webhooks/{id}` | Remove a webhook (owner only) |
| GET | `/ad.svg` | Ad Creator social graphic |
| GET/POST | `/codes` | Discount/waiver codes (owner only for POST) |
| DELETE | `/codes/{id}` | Delete a code (owner only) |

---

## Frontend routes

| Path | Page | Audience |
|---|---|---|
| `/` | Home | Everyone |
| `/help` | Help Center | Everyone |
| `/login`, `/register` | Auth | Everyone |
| `/festivals`, `/festivals/:slug` | Festival directory & public profile | Everyone |
| `/dashboard` | Film library, submissions, credits, notifications | Filmmaker |
| `/films/new`, `/films/:id/scores` | Add a project, view scores + guidance | Filmmaker |
| `/submit` | Submit form (categories, codes, custom questions, cover letter) | Filmmaker |
| `/credits` | Buy scoring credits | Filmmaker |
| `/reviews/new` | Leave a festival review | Filmmaker |
| `/festival/dashboard` | Submissions manager + every organizer tool card | Organizer |
| `/festival/submissions/:id` | Full judging view: media, judges, rating, log, notes | Organizer |

Owner-only cards (profile, staff, rubric, custom form, flags, messages,
discounts, waiver period, webhooks, ad creator, laurel center, marketing,
transactions, reports) render only for the `owner` role and are also
enforced at the API layer — a non-owner hitting them directly gets 403.

---

## Design system

Defined in [frontend/src/styles.css](../frontend/src/styles.css), per BRD
§6:

- **Palette**: Reel Ink, Marquee Amber, Darkroom Teal, Paper White, Soft
  Charcoal, Hairline — film-world warmth instead of generic SaaS blue.
- **Typography**: serif display headings (Georgia) for titles and scores;
  humanist sans for body/UI; 16px minimum body text.
- **Layout**: single-column mobile, calm two-column desktop; tables
  collapse into labeled cards under 700px.
- **Signature element**: the circular Fit Score dial, animated once on
  reveal, respecting `prefers-reduced-motion`.
- **Accessibility**: WCAG AA contrast, visible focus states, 44×44px
  touch targets, no icon-only navigation.
- Costly or destructive actions (scoring, submitting, revoking contact,
  deleting a code/flag/webhook) always require an explicit confirm step.

---

## Demo data

Running `python -m scripts.seed` creates 6 festivals and 3 accounts
(password `reelfit-demo` for all):

| Account | Role |
|---|---|
| `priya@example.com` | Filmmaker — 2 films + 1 screenplay, 3 scoring credits |
| `organizer@example.com` | Owner of Hillside Film Festival (Arjun Mehta) |
| `jury@example.com` | Jury member on Hillside (Divya Kapoor) |

Hillside is seeded with a full rubric, two custom questions, three flags,
three discount/waiver codes, a 14-day deadline waiver window, and demo
marketing traffic across three sources — enough to exercise every
organizer-tool card without further setup.

---

## Deferred & rejected items

Recorded so they aren't silently relitigated (BRD §9):

- Public review/ratings **aggregator** as a standalone product —
  rejected; Reelfit's reviews are submission-verified only, never open
  registration-based ratings.
- Manual festival verification/curation as the **primary** offering —
  rejected; the calibration badge and honest analytics are the
  structural differentiator instead.
- IMDb credit-bridge automation — real gap, deferred to a later phase.
- Reelfit as a **distribution aggregator or sales agent** — explicitly
  out of scope; the recommendations module only recommends.
- Regional-only scope — rejected.
- Celery/Redis background job queue, Alembic migrations, and S3 object
  storage for media — Phase 1 uses synchronous calls, `create_all()`,
  and stored URLs respectively; all three are the acknowledged next
  infrastructure step before a production launch.
- Payment processing is a dev-mode stand-in; Stripe integration attaches
  behind `payments/service.py` without changing any caller.
- Festival licensing invoicing UI (the ledger model exists; no admin
  screen yet).
