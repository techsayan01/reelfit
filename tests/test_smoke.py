"""End-to-end smoke tests over the JSON API: register, add a film, score it,
submit, review — plus calibration labels, eligibility, and role guards."""

from datetime import date, timedelta

from app.db import SessionLocal
from app.modules.festivals import service as festivals_svc
from app.modules.festivals.models import (
    Category, CategoryKind, DeadlineTier, Festival, FestivalEdition,
)


def _seed_festival(history: int = 40, is_public: bool = True) -> int:
    db = SessionLocal()
    today = date.today()
    fest = Festival(
        name="Test Fest", slug="test-fest", description="A test festival",
        is_public=is_public, founded_year=today.year - 2,
        rules="English subtitles required.",
    )
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
    db.add(Category(
        edition_id=edition.id, name="Feature Script",
        kind=CategoryKind.SCREENPLAY, base_fee_cents=4500,
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


def test_festival_public_profile(client):
    _seed_festival()
    resp = client.get("/api/festivals/test-fest")
    assert resp.status_code == 200
    data = resp.json()
    assert data["festival"]["rules"] == "English subtitles required."
    assert data["stats"]["years_running"] == 3
    assert data["stats"]["total_submissions"] == 0
    # Timeline: opening date + one deadline tier
    labels = [t["label"] for t in data["timeline"]]
    assert "Opening date" in labels and "Regular" in labels
    assert any(t["is_current"] for t in data["timeline"])


def test_non_public_festival_hidden(client):
    _seed_festival(is_public=False)
    assert client.get("/api/festivals").json()["festivals"] == []
    assert client.get("/api/festivals/test-fest").status_code == 404


def test_screenplay_flow(client):
    _seed_festival()
    _register_filmmaker(client)
    # Screenplay project: no runtime
    resp = client.post("/api/films", json={
        "title": "The Last Projectionist", "kind": "screenplay",
        "genre": "drama", "year": date.today().year,
    })
    assert resp.status_code == 201
    film_id = resp.json()["film"]["id"]

    # A film without runtime is rejected
    resp = client.post("/api/films", json={
        "title": "No Runtime Film", "kind": "film",
        "genre": "drama", "year": date.today().year,
    })
    assert resp.status_code == 400

    # Only the screenplay category is eligible
    resp = client.get(f"/api/submissions/options?film={film_id}&festival=1")
    cats = resp.json()["categories"]
    assert [c["name"] for c in cats] == ["Feature Script"]

    # Scoring a screenplay works (runtime component neutral)
    resp = client.post(f"/api/films/{film_id}/score")
    assert resp.status_code == 200

    # Submitting to the screenplay category works
    resp = client.post("/api/submissions", json={
        "film_id": film_id, "festival_id": 1, "category_id": cats[0]["id"],
    })
    assert resp.status_code == 201


def test_profile_update_owner_only(client):
    _seed_festival()
    # Organizer registered without a festival gets 403 on the dashboard;
    # register one with a festival, then edit its profile.
    resp = client.post("/api/auth/register", json={
        "email": "org@example.com", "password": "password123",
        "display_name": "Org", "kind": "organizer", "festival_name": "My New Fest",
    })
    assert resp.status_code == 200
    resp = client.patch("/api/festival/profile", json={
        "venue_name": "Tapaste Cafe", "founded_year": 2023, "rules": "New rules.",
    })
    assert resp.status_code == 200
    assert resp.json()["festival"]["venue_name"] == "Tapaste Cafe"

    resp = client.get("/api/festival/dashboard")
    assert resp.json()["can_edit_profile"] is True


def test_tracking_numbers_sequential(client):
    _seed_festival()
    _register_filmmaker(client)
    ids = []
    for i, title in enumerate(["Film A", "Film B"]):
        resp = client.post("/api/films", json={
            "title": title, "genre": "documentary",
            "runtime_minutes": 20, "year": date.today().year,
        })
        film_id = resp.json()["film"]["id"]
        resp = client.post("/api/submissions", json={
            "film_id": film_id, "festival_id": 1, "category_id": 1,
        })
        ids.append(resp.json()["submission"]["id"])
    subs = client.get("/api/submissions").json()["submissions"]
    numbers = sorted(s["tracking_number"] for s in subs)
    # Default prefix from "Test Fest" initials, sequential from 1001.
    assert numbers == ["TES1001", "TES1002"]


def test_award_status_grants_certificate(client):
    _seed_festival()
    _register_filmmaker(client)
    resp = client.post("/api/films", json={
        "title": "Winner", "genre": "documentary",
        "runtime_minutes": 20, "year": date.today().year,
    })
    film_id = resp.json()["film"]["id"]
    sub_id = client.post("/api/submissions", json={
        "film_id": film_id, "festival_id": 1, "category_id": 1,
    }).json()["submission"]["id"]

    # Organizer takes over their own festival and awards the film.
    client.post("/api/auth/register", json={
        "email": "org2@example.com", "password": "password123",
        "display_name": "Org", "kind": "organizer",
    })
    from app.db import SessionLocal
    from app.modules.accounts.models import FestivalMembership, OrgRole
    db = SessionLocal()
    org_id = 2  # second registered user
    db.add(FestivalMembership(user_id=org_id, festival_id=1, role=OrgRole.OWNER))
    db.commit()
    db.close()
    resp = client.post(f"/api/festival/submissions/{sub_id}/status", json={
        "status": "award_winner",
    })
    assert resp.status_code == 200
    dash = client.get("/api/festival/dashboard").json()
    row = next(s for s in dash["submissions"] if s["id"] == sub_id)
    assert row["status"] == "award_winner"
    assert row["notified"] is True

    # Filmmaker can download the laurel for an award-winner status.
    client.post("/api/auth/login", json={
        "email": "p@example.com", "password": "password123",
    })
    resp = client.get(f"/api/submissions/{sub_id}/certificate.svg")
    assert resp.status_code == 200
    assert "OFFICIAL SELECTION" in resp.text


def test_submission_detail_with_log_and_notes(client):
    _seed_festival()
    _register_filmmaker(client)
    film_id = client.post("/api/films", json={
        "title": "Detail Film", "genre": "documentary",
        "runtime_minutes": 20, "year": date.today().year,
        "synopsis": "A film about details.",
        "credits": "A Person — Director",
        "screener_url": "https://www.youtube.com/watch?v=abc12345678",
    }).json()["film"]["id"]
    sub_id = client.post("/api/submissions", json={
        "film_id": film_id, "festival_id": 1, "category_id": 1,
        "cover_letter": "Please consider us.",
    }).json()["submission"]["id"]

    client.post("/api/auth/register", json={
        "email": "org3@example.com", "password": "password123",
        "display_name": "Org Three", "kind": "organizer",
    })
    from app.db import SessionLocal
    from app.modules.accounts.models import FestivalMembership, OrgRole
    db = SessionLocal()
    db.add(FestivalMembership(user_id=2, festival_id=1, role=OrgRole.OWNER))
    db.commit()
    db.close()

    # Status change is logged with the actor
    client.post(f"/api/festival/submissions/{sub_id}/status", json={"status": "shortlisted"})
    # Internal note
    resp = client.post(f"/api/festival/submissions/{sub_id}/notes", json={
        "text": "Strong opening ten minutes.",
    })
    assert resp.status_code == 201

    resp = client.get(f"/api/festival/submissions/{sub_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["film"]["synopsis"] == "A film about details."
    assert data["submission"]["cover_letter"] == "Please consider us."
    assert data["filmmaker"]["display_name"] == "Priya"
    # Masked contact: relay handle, never an email
    assert "@" not in data["submission"]["contact"]
    assert data["status_log"][0]["actor"] == "Org Three"
    assert data["status_log"][0]["to_status"] == "shortlisted"
    assert data["notes"][0]["text"] == "Strong opening ten minutes."
    assert data["prev_id"] is None and data["next_id"] is None


def test_jury_assignment_and_rating(client):
    _seed_festival()
    _register_filmmaker(client)
    film_id = client.post("/api/films", json={
        "title": "Rated Film", "genre": "documentary",
        "runtime_minutes": 20, "year": date.today().year,
    }).json()["film"]["id"]
    sub_id = client.post("/api/submissions", json={
        "film_id": film_id, "festival_id": 1, "category_id": 1,
    }).json()["submission"]["id"]

    # Owner (user 2) with a jury member (user 3)
    client.post("/api/auth/register", json={
        "email": "owner@example.com", "password": "password123",
        "display_name": "Owner", "kind": "organizer",
    })
    client.post("/api/auth/register", json={
        "email": "juror@example.com", "password": "password123",
        "display_name": "Juror", "kind": "organizer",
    })
    from app.db import SessionLocal
    from app.modules.accounts.models import FestivalMembership, OrgRole
    db = SessionLocal()
    db.add(FestivalMembership(user_id=2, festival_id=1, role=OrgRole.OWNER))
    db.commit()
    db.close()

    client.post("/api/auth/login", json={
        "email": "owner@example.com", "password": "password123",
    })
    # Owner builds a rubric and adds the juror as staff
    assert client.post("/api/festival/rubric", json={
        "name": "Storytelling", "weight": 2,
    }).status_code == 201
    crit2 = client.post("/api/festival/rubric", json={"name": "Craft"}).json()["id"]
    assert client.post("/api/festival/staff", json={
        "email": "juror@example.com", "role": "jury",
    }).status_code == 201
    # Duplicate staff rejected
    assert client.post("/api/festival/staff", json={
        "email": "juror@example.com", "role": "jury",
    }).status_code == 400

    # Assign the juror (user 3)
    assert client.post(f"/api/festival/submissions/{sub_id}/assign", json={
        "user_id": 3,
    }).status_code == 200

    # Juror sees the queue and rates
    client.post("/api/auth/login", json={
        "email": "juror@example.com", "password": "password123",
    })
    queue = client.get("/api/festival/queue").json()["queue"]
    assert len(queue) == 1 and queue[0]["film_title"] == "Rated Film"
    rubric = client.get("/api/festival/rubric").json()["criteria"]
    assert client.post(f"/api/festival/submissions/{sub_id}/rate", json={
        "scores": [
            {"criterion_id": rubric[0]["id"], "score": 9},
            {"criterion_id": crit2, "score": 6},
        ],
    }).status_code == 200

    # Weighted average: (9*2 + 6*1) / 3 = 8.0
    detail = client.get(f"/api/festival/submissions/{sub_id}").json()
    assert detail["rating"] == {"average": 8.0, "judges": 1}
    assert detail["judges"][0]["name"] == "Juror"
    assert detail["judges"][0]["status"] == "done"

    # Rating appears in the dashboard list; queue is now clear
    dash = client.get("/api/festival/dashboard").json()
    assert dash["submissions"][0]["rating"] == 8.0
    assert client.get("/api/festival/queue").json()["queue"] == []

    # Jury role can't change judging status or manage staff
    assert client.post(f"/api/festival/submissions/{sub_id}/status", json={
        "status": "selected",
    }).status_code == 403
    assert client.post("/api/festival/staff", json={
        "email": "p@example.com", "role": "viewer",
    }).status_code == 403


def _make_owner(client, email="codeowner@example.com"):
    client.post("/api/auth/register", json={
        "email": email, "password": "password123",
        "display_name": "Code Owner", "kind": "organizer",
    })
    from app.db import SessionLocal
    from app.modules.accounts.models import FestivalMembership, OrgRole, User
    from sqlalchemy import select
    db = SessionLocal()
    user = db.scalar(select(User).where(User.email == email))
    db.add(FestivalMembership(user_id=user.id, festival_id=1, role=OrgRole.OWNER))
    db.commit()
    db.close()


def test_discount_and_waiver_codes(client):
    _seed_festival()
    _make_owner(client)

    # Owner creates a fee-waiver code limited to one use per submitter
    resp = client.post("/api/festival/codes", json={
        "code": "outreach26", "code_type": "fee_waiver",
        "label": "Outreach", "one_use_per_submitter": True,
    })
    assert resp.status_code == 201
    assert resp.json()["code"] == "OUTREACH26"
    # Duplicate rejected; bad percent rejected
    assert client.post("/api/festival/codes", json={
        "code": "OUTREACH26", "code_type": "fee_waiver",
    }).status_code == 400
    assert client.post("/api/festival/codes", json={
        "code": "BADPCT", "code_type": "discount", "kind": "percent", "amount": 150,
    }).status_code == 400

    # Filmmaker uses the waiver: fee becomes 0
    _register_filmmaker(client, email="w@example.com")
    film_id = client.post("/api/films", json={
        "title": "Waived Film", "genre": "documentary",
        "runtime_minutes": 20, "year": date.today().year,
    }).json()["film"]["id"]
    resp = client.post("/api/submissions", json={
        "film_id": film_id, "festival_id": 1, "category_id": 1,
        "discount_code": "OUTREACH26",
    })
    assert resp.status_code == 201
    assert resp.json()["submission"]["fee_paid_cents"] == 0

    # One-use-per-submitter: same filmmaker can't use it again
    film2 = client.post("/api/films", json={
        "title": "Second Film", "genre": "documentary",
        "runtime_minutes": 22, "year": date.today().year,
    }).json()["film"]["id"]
    resp = client.post("/api/submissions", json={
        "film_id": film2, "festival_id": 1, "category_id": 1,
        "discount_code": "OUTREACH26",
    })
    assert resp.status_code == 400


def test_deadline_waiver_flow(client):
    # Festival whose edition closed 3 days ago, with a 14-day waiver window
    db = SessionLocal()
    today = date.today()
    fest = Festival(name="Closed Fest", slug="closed-fest", deadline_waiver_days=14)
    db.add(fest)
    db.flush()
    edition = FestivalEdition(
        festival_id=fest.id, label="2026",
        opens_on=today - timedelta(days=90), closes_on=today - timedelta(days=3),
    )
    db.add(edition)
    db.flush()
    db.add(Category(
        edition_id=edition.id, name="Short Film",
        min_runtime_minutes=1, max_runtime_minutes=40, base_fee_cents=3000,
    ))
    db.add(DeadlineTier(
        edition_id=edition.id, name="Late",
        deadline=today - timedelta(days=3), fee_delta_cents=1500,
    ))
    db.commit()
    db.close()

    _make_owner(client)
    client.post("/api/festival/codes", json={
        "code": "LATEPASS", "code_type": "deadline_waiver",
    })

    _register_filmmaker(client, email="late@example.com")
    film_id = client.post("/api/films", json={
        "title": "Late Film", "genre": "drama",
        "runtime_minutes": 15, "year": today.year,
    }).json()["film"]["id"]

    # Without a waiver code: rejected
    resp = client.post("/api/submissions", json={
        "film_id": film_id, "festival_id": 1, "category_id": 1,
    })
    assert resp.status_code == 400
    assert "deadline waiver" in resp.json()["detail"]

    # Options endpoint flags the waiver window
    resp = client.get(f"/api/submissions/options?film={film_id}&festival=1")
    assert resp.json()["waiver_required"] is True

    # With the code: accepted at the late-tier fee (3000 + 1500)
    resp = client.post("/api/submissions", json={
        "film_id": film_id, "festival_id": 1, "category_id": 1,
        "discount_code": "LATEPASS",
    })
    assert resp.status_code == 201
    assert resp.json()["submission"]["fee_paid_cents"] == 4500


def test_custom_form_flags_messages_insights(client):
    _seed_festival()
    _make_owner(client, email="owner6@example.com")

    # Custom submission form: a yes/no and a dropdown question
    q1 = client.post("/api/festival/questions", json={
        "field_type": "yes_no", "question": "Did you attend film school?",
    }).json()["id"]
    q2 = client.post("/api/festival/questions", json={
        "field_type": "dropdown", "question": "How did you hear about us?",
        "options": "Instagram\nA friend\nOther",
    }).json()["id"]
    # Dropdown with < 2 options rejected
    assert client.post("/api/festival/questions", json={
        "field_type": "dropdown", "question": "Bad", "options": "Only one",
    }).status_code == 400

    # Flags + default judging form
    flag_id = client.post("/api/festival/flags", json={
        "name": "Strong contender", "color": "#2E7D46",
    }).json()["id"]
    assert client.post("/api/festival/rubric/defaults", json={}).status_code == 201
    rubric = client.get("/api/festival/rubric").json()["criteria"]
    assert len(rubric) == 9  # standard film judging form

    # Filmmaker submits: missing answers rejected, wrong dropdown rejected
    _register_filmmaker(client, email="q@example.com")
    film_id = client.post("/api/films", json={
        "title": "Answered Film", "genre": "documentary",
        "runtime_minutes": 20, "year": date.today().year,
    }).json()["film"]["id"]
    assert client.post("/api/submissions", json={
        "film_id": film_id, "festival_id": 1, "category_id": 1,
    }).status_code == 400
    assert client.post("/api/submissions", json={
        "film_id": film_id, "festival_id": 1, "category_id": 1,
        "answers": {str(q1): "Yes", str(q2): "Not an option"},
    }).status_code == 400
    sub_id = client.post("/api/submissions", json={
        "film_id": film_id, "festival_id": 1, "category_id": 1,
        "answers": {str(q1): "Yes", str(q2): "Instagram"},
    }).json()["submission"]["id"]

    # Owner: flag it, rate with comment + recommendation, read the detail
    client.post("/api/auth/login", json={
        "email": "owner6@example.com", "password": "password123",
    })
    assert client.post(f"/api/festival/submissions/{sub_id}/flag", json={
        "flag_id": flag_id,
    }).status_code == 200
    client.post(f"/api/festival/submissions/{sub_id}/rate", json={
        "scores": [{"criterion_id": rubric[0]["id"], "score": 8}],
        "comment": "Lovely opening.", "recommendation": "recommend",
    })
    detail = client.get(f"/api/festival/submissions/{sub_id}").json()
    answers = {a["question"]: a["answer"] for a in detail["custom_answers"]}
    assert answers["Did you attend film school?"] == "Yes"
    assert detail["submission"]["flag_id"] == flag_id
    assert detail["judges"][0]["recommendation"] == "recommend"
    assert detail["judges"][0]["comment"] == "Lovely opening."

    # Flag shows in the dashboard list
    dash = client.get("/api/festival/dashboard").json()
    assert dash["submissions"][0]["flag"]["name"] == "Strong contender"

    # Insights: one judge, 1/1 judged
    insights = client.get("/api/festival/insights").json()
    assert insights["totals"] == {
        "judges": 1, "submissions": 1, "judged": 1, "not_judged": 0, "pct_judged": 100,
    }
    assert insights["judges"][0]["runtime_minutes_assigned"] == 20

    # Bulk message to submitters lands in the filmmaker's notifications
    resp = client.post("/api/festival/messages", json={
        "audience": "submitters", "subject": "Screening date announced",
        "body": "Join us on the 16th!",
    })
    assert resp.status_code == 201
    assert resp.json()["recipient_count"] == 1
    assert len(client.get("/api/festival/messages").json()["messages"]) == 1

    client.post("/api/auth/login", json={
        "email": "q@example.com", "password": "password123",
    })
    notes = client.get("/api/submissions").json()["notifications"]
    assert any("Screening date announced" in n["subject"] for n in notes)


def test_festival_dashboard_requires_organizer(client):
    _register_filmmaker(client)
    resp = client.get("/api/festival/dashboard")
    assert resp.status_code == 403


def test_credits_purchase(client):
    _register_filmmaker(client)
    resp = client.post("/api/credits/buy", json={"pack": "trio"})
    assert resp.status_code == 200
    assert resp.json()["credit_balance"] == 4  # 1 welcome + 3
