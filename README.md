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

- `priya@example.com` — filmmaker with two films and 3 scoring credits
- `organizer@example.com` — owner of Hillside Film Festival

Run tests: `pytest`

## Architecture

Single Python application, decomposable by design. Each package under
`app/modules/` owns its models and exposes a `service.py` — modules never
import each other's internals, only service layers:

| Module | Owns |
|---|---|
| `accounts` | users, roles, festival staff membership, film library |
| `festivals` | listings, editions, categories, deadline tiers, historical selections |
| `discounts` | promo codes, fee waivers |
| `jury` | reviewer assignment, rubrics, internal notes |
| `submissions` | submission workflow, masked-contact relay |
| `scoring` | the fit-scoring engine + calibration status |
| `recommendations` | festival ranking, distribution guidance |
| `reviews` | submission-verified reviews, festival right-of-reply |
| `payments` | fees, credit packs, ledger (Stripe boundary) |
| `dashboards` | festival- and filmmaker-side aggregates |
| `certificates` | laurel/certificate generation |
| `notifications` | in-app + email notifications |

The HTTP layer (`app/api/`) exposes a session-cookie-authenticated JSON API
(interactive docs at `/internal/docs`). The React SPA (`frontend/`) follows
the BRD design system: warm palette (Marquee Amber / Darkroom Teal on Paper
White), serif headings, 44px touch targets, mobile-first responsive layout
(stacked cards under 700px, calm two-column above), and the circular Fit
Score dial as the signature element.

## Phase 1 notes

- **Scoring engine** is a transparent heuristic baseline (genre affinity vs.
  the festival's own base rate, runtime fit, recency) behind a stable
  interface; the ML model replaces it without touching callers. Festivals
  under 30 confirmed historical outcomes are labeled *calibrating* and every
  score carries that label.
- **Payments** run through a dev provider locally; Stripe drops in behind
  `payments/service.py`.
- **Recommendation persistence** (BRD §7.4 entity) is computed on demand for
  now; becomes a table when frozen snapshots are needed.
- Celery/Redis, Alembic migrations, and object storage are wired in as the
  next infrastructure step before production.
