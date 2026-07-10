# Reelfit

Festival fit-scoring & distribution-guidance platform. Reelfit scores a film
against a festival's **actual selection history** before the filmmaker pays a
submission fee, and gives festivals consistent AI-assisted judging plus the
submission analytics incumbents don't offer.

Phase 1 is a deliberately structured monolith (see the BRD): a FastAPI +
SQLAlchemy 2.0 JSON API with a responsive React (Vite) SPA, PostgreSQL in
production, SQLite for local dev.

## Quick start

```bash
# Backend API (port 8000)
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m scripts.seed          # founding-cohort demo data
uvicorn app.main:app --reload

# Frontend (port 5173, proxies /api to the backend)
cd frontend && npm install && npm run dev
```

For a single-server production-style run, build the SPA and let FastAPI
serve it: `cd frontend && npm run build`, then open http://localhost:8000.

Demo accounts (password `reelfit-demo`):

- `priya@example.com` — filmmaker with two films, a screenplay, and 3 scoring credits
- `organizer@example.com` — owner of Hillside Film Festival (Arjun Mehta)
- `jury@example.com` — jury member on Hillside (Divya Kapoor)

Run tests: `pytest` (18 end-to-end API tests)

**Full feature reference, API docs, and data model: [docs/FEATURES.md](docs/FEATURES.md).**

## Architecture

Single Python application, decomposable by design. Each package under
`app/modules/` owns its models and exposes a `service.py` — modules never
import each other's internals, only service layers:

| Module | Owns |
|---|---|
| `accounts` | users, roles, festival staff membership, film/screenplay library |
| `festivals` | listings, editions, categories, deadline tiers, custom form questions, flags, tracking visits, historical selections |
| `discounts` | discount/fee-waiver/deadline-waiver codes, redemptions |
| `jury` | reviewer assignment, rubrics, ratings, internal notes |
| `submissions` | submission workflow, masked-contact relay, custom answers, status audit log, export configs |
| `scoring` | the fit-scoring engine + calibration status |
| `recommendations` | festival ranking, distribution guidance |
| `reviews` | submission-verified reviews, festival right-of-reply |
| `payments` | fees, credit packs, ledger (Stripe boundary) |
| `dashboards` | festival- and filmmaker-side aggregates |
| `certificates` | laurel/certificate generation, laurel & ad-creator SVG rendering |
| `notifications` | in-app notifications, bulk messaging, webhooks |

The HTTP layer (`app/api/`) exposes a session-cookie-authenticated JSON API
(interactive docs at `/internal/docs`). The React SPA (`frontend/`) follows
the BRD design system: warm palette (Marquee Amber / Darkroom Teal on Paper
White), serif headings, 44px touch targets, mobile-first responsive layout
(stacked cards under 700px, calm two-column above), and the circular Fit
Score dial as the signature element.

Beyond the BRD's Phase 1 slice, the festival side now covers the operational
surface a real festival needs day to day — staff & judge management, a
configurable scoring rubric and review queues, discount/waiver codes with a
deadline-waiver window, a custom submission form, colored flags, bulk
messaging, webhooks, and honest conversion analytics (views → submissions by
traffic source, computed from real records, never self-reported). See
**[docs/FEATURES.md](docs/FEATURES.md)** for the full breakdown, mapped to
BRD sections, with every API route and data model documented.

## Phase 1 notes

- **Scoring engine** is a transparent heuristic baseline (genre affinity vs.
  the festival's own base rate, runtime fit, recency) behind a stable
  interface; the ML model replaces it without touching callers. Festivals
  under 30 confirmed historical outcomes are labeled *calibrating* and every
  score carries that label.
- **Payments** run through a dev provider locally; Stripe drops in behind
  `payments/service.py`.
- **Webhooks** deliver best-effort from a background thread; production
  moves delivery to a retrying Celery task behind the same
  `notifications/service.py` interface.
- **Recommendation persistence** (BRD §7.4 entity) is computed on demand for
  now; becomes a table when frozen snapshots are needed.
- Celery/Redis, Alembic migrations, and object storage are wired in as the
  next infrastructure step before production.
