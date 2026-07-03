"""End-to-end smoke tests over the JSON API: register, add a film, score it,
submit, review — plus calibration labels, eligibility, and role guards."""

from datetime import date, timedelta

from app.db import SessionLocal
from app.modules.festivals import service as festivals_svc
from app.modules.festivals.models import Category, DeadlineTier, Festival, FestivalEdition


def _seed_festival(history: int = 40) -> int:
    db = SessionLocal()
    today = date.today()
    fest = Festival(name="Test Fest", slug="test-fest", description="A test festival")
    db.add(fest)
    db.flush()
    edition = FestivalEdition(
        festival_id=fest.id, label="2026",
        opens_on=today - timedelta(days=10), closes_on=today + timedelta(days=60),
    )
    db.add(edition)
    db.flush()
    db.add(Category(
        edition_id=edition.id, name="Short Film",
        min_runtime_minutes=1, max_runtime_minutes=40, base_fee_cents=3000,
    ))
    db.add(DeadlineTier(
        edition_id=edition.id, name="Regular",
        deadline=today + timedelta(days=30), fee_delta_cents=0,
    ))
    for i in range(history):
        festivals_svc.ingest_historical_selection(
            db, fest.id, genre="documentary", runtime_minutes=20,
            year=today.year - 1, selected=(i % 3 == 0),
        )
    db.commit()
    fest_id = fest.id
    db.close()
    return fest_id


def _register_filmmaker(client, email="p@example.com"):
    resp = client.post("/api/auth/register", json={
        "email": email, "password": "password123",
        "display_name": "Priya", "kind": "filmmaker",
    })
    assert resp.status_code == 200
    assert resp.json()["user"]["credit_balance"] == 1


def test_me_unauthenticated(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 200
    assert resp.json()["user"] is None


def test_full_filmmaker_flow(client):
    _seed_festival()
    _register_filmmaker(client)

    # Add a film
    resp = client.post("/api/films", json={
        "title": "Monsoon Letters", "genre": "documentary",
        "runtime_minutes": 24, "year": date.today().year - 1,
    })
    assert resp.status_code == 201
    film_id = resp.json()["film"]["id"]

    # Score it (welcome credit covers this)
    resp = client.post(f"/api/films/{film_id}/score")
    assert resp.status_code == 200
    assert resp.json()["credit_balance"] == 0

    resp = client.get(f"/api/films/{film_id}/scores")
    assert resp.status_code == 200
    data = resp.json()
    assert data["scores"][0]["festival"]["name"] == "Test Fest"
    assert data["scores"][0]["calibration_status"] == "validated"
    assert len(data["guidance"]) >= 1

    # Out of credits: 402
    resp = client.post(f"/api/films/{film_id}/score")
    assert resp.status_code == 402

    # Eligible categories for the submit form
    resp = client.get(f"/api/submissions/options?film={film_id}&festival=1")
    assert resp.status_code == 200
    category_id = resp.json()["categories"][0]["id"]

    # Submit the film
    resp = client.post("/api/submissions", json={
        "film_id": film_id, "festival_id": 1, "category_id": category_id,
    })
    assert resp.status_code == 201
    submission_id = resp.json()["submission"]["id"]

    # Duplicate submission blocked
    resp = client.post("/api/submissions", json={
        "film_id": film_id, "festival_id": 1, "category_id": category_id,
    })
    assert resp.status_code == 400
    assert "already submitted" in resp.json()["detail"]

    # Submission-received notification exists
    resp = client.get("/api/submissions")
    data = resp.json()
    assert len(data["submissions"]) == 1
    assert any("was sent to" in n["subject"] for n in data["notifications"])

    # Review the festival (verified: real submission exists)
    resp = client.post("/api/reviews", json={
        "submission_id": submission_id, "rating": 4,
        "text": "Well run and responsive.",
    })
    assert resp.status_code == 201

    # Review visible publicly, duplicate blocked
    resp = client.get("/api/festivals/test-fest")
    assert resp.json()["reviews"][0]["text"] == "Well run and responsive."
    resp = client.post("/api/reviews", json={
        "submission_id": submission_id, "rating": 5, "text": "again",
    })
    assert resp.status_code == 400


def test_scoring_calibration_labels(client):
    _seed_festival(history=5)  # below validation threshold
    _register_filmmaker(client)
    resp = client.post("/api/films", json={
        "title": "Small Film", "genre": "drama",
        "runtime_minutes": 12, "year": date.today().year,
    })
    film_id = resp.json()["film"]["id"]
    client.post(f"/api/films/{film_id}/score")
    resp = client.get(f"/api/films/{film_id}/scores")
    assert resp.json()["scores"][0]["calibration_status"] == "calibrating"


def test_ineligible_runtime_rejected(client):
    _seed_festival()
    _register_filmmaker(client)
    resp = client.post("/api/films", json={
        "title": "Long Epic", "genre": "drama",
        "runtime_minutes": 180, "year": date.today().year,
    })
    film_id = resp.json()["film"]["id"]
    resp = client.post("/api/submissions", json={
        "film_id": film_id, "festival_id": 1, "category_id": 1,
    })
    assert resp.status_code == 400


def test_festival_dashboard_requires_organizer(client):
    _register_filmmaker(client)
    resp = client.get("/api/festival/dashboard")
    assert resp.status_code == 403


def test_credits_purchase(client):
    _register_filmmaker(client)
    resp = client.post("/api/credits/buy", json={"pack": "trio"})
    assert resp.status_code == 200
    assert resp.json()["credit_balance"] == 4  # 1 welcome + 3
