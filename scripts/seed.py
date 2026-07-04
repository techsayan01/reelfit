"""Seed the founding cohort: partner festivals with editions, categories,
deadline tiers, historical selection data, and demo accounts.

Usage:  python -m scripts.seed
Demo accounts (password for all: reelfit-demo):
  priya@example.com     — filmmaker with two films and 3 credits
  organizer@example.com — owner of Hillside Film Festival
"""

import random
from datetime import date, timedelta

from app.db import SessionLocal, create_all
from app.modules.accounts.models import FestivalMembership, OrgRole, ProjectKind, UserKind
from app.modules.accounts import service as accounts
from app.modules.discounts.models import CodeType, DiscountCode, DiscountKind
from app.modules.festivals import service as festivals_svc
from app.modules.festivals.models import (
    CalibrationStatus, Category, CategoryKind, DeadlineTier, Festival, FestivalEdition,
)

FESTIVALS = [
    # (name, country, region, description, history_size, genre_bias)
    ("Hillside Film Festival", "India", "Asia",
     "The founder's own festival — documentary and drama focused, "
     "with two months of live Reelfit scoring already behind it.", 80,
     {"documentary": 0.35, "drama": 0.30}),
    ("Coastal Shorts", "India", "Asia",
     "A shorts-only festival with a soft spot for comedy and animation.", 45,
     {"comedy": 0.40, "animation": 0.30}),
    ("Northlight Docs", "Norway", "Europe",
     "Documentary features about people and places on the margins.", 60,
     {"documentary": 0.60}),
    ("Midnight Frame", "USA", "North America",
     "Genre cinema after dark: horror, thriller, the strange.", 35,
     {"horror": 0.45, "thriller": 0.35}),
    ("First Reel Student Fest", "India", "Asia",
     "Student and first-time filmmakers only. New this year — scoring still calibrating.", 8,
     {"drama": 0.30}),
    ("Riverbank International", "UK", "Europe",
     "A broad international program across features and shorts.", 50,
     {"drama": 0.25, "documentary": 0.25}),
]

GENRES = ["drama", "comedy", "documentary", "horror", "thriller", "animation", "experimental"]


def seed() -> None:
    create_all()
    db = SessionLocal()
    rng = random.Random(42)
    today = date.today()

    if db.query(Festival).count() > 0:
        print("Database already seeded — skipping.")
        return

    fests = []
    for i, (name, country, region, desc, history_n, bias) in enumerate(FESTIVALS):
        slug = name.lower().replace(" ", "-")
        fest = Festival(
            name=name, slug=slug, description=desc, country=country, region=region,
            calibration_status=(
                CalibrationStatus.VALIDATED if history_n >= 30
                else CalibrationStatus.CALIBRATING
            ),
            rules=(
                "All entries must include a screener link. Non-English films need "
                "English subtitles. Multiple submissions are allowed, one entry "
                "per project per category. Fees are non-refundable once judging begins."
            ),
            contact_email=f"hello@{slug.replace('-', '')}.example.com",
            website=f"https://{slug.replace('-', '')}.example.com",
            founded_year=today.year - (3 + i % 4),
        )
        if i == 0:
            # The founder's festival gets the full FilmFreeway-parity profile.
            fest.venue_name = "Tapaste - The Spanish Cafe & Restaurant"
            fest.venue_address = "Kolkata, West Bengal 700029, India"
            fest.instagram = "https://instagram.com/hillsidefest"
            fest.twitter = "https://x.com/hillsidefest"
            fest.phone = "+91 98300 00000"
            fest.tracking_prefix = "HIL"
            fest.deadline_waiver_days = 14
            fest.awards_and_prizes = (
                "Every selected film receives official laurels and a screening "
                "at the annual event. Winners in each main category receive a "
                "certificate and a live Q&A slot. Finalists receive certificates."
            )
        db.add(fest)
        db.flush()
        fests.append(fest)

        edition = FestivalEdition(
            festival_id=fest.id, label=str(today.year),
            opens_on=today - timedelta(days=30),
            closes_on=today + timedelta(days=90),
            notification_on=today + timedelta(days=150),
        )
        db.add(edition)
        db.flush()

        shorts_only = "shorts" in name.lower() or "student" in name.lower()
        cats = [Category(
            edition_id=edition.id, name="Short Film",
            min_runtime_minutes=1, max_runtime_minutes=40, base_fee_cents=3000,
        )]
        if not shorts_only:
            cats.append(Category(
                edition_id=edition.id, name="Feature Film",
                min_runtime_minutes=41, max_runtime_minutes=240, base_fee_cents=8700,
            ))
            cats.append(Category(
                edition_id=edition.id, name="Documentary",
                min_runtime_minutes=20, max_runtime_minutes=240, base_fee_cents=5500,
            ))
            cats.append(Category(
                edition_id=edition.id, name="Feature Script / Screenplay",
                kind=CategoryKind.SCREENPLAY, base_fee_cents=4500,
            ))
        db.add_all(cats)

        db.add_all([
            DeadlineTier(edition_id=edition.id, name="Early bird",
                         deadline=today + timedelta(days=20), fee_delta_cents=-1000),
            DeadlineTier(edition_id=edition.id, name="Regular",
                         deadline=today + timedelta(days=60), fee_delta_cents=0),
            DeadlineTier(edition_id=edition.id, name="Late",
                         deadline=today + timedelta(days=90), fee_delta_cents=1500),
        ])

        # Historical selections shaped by each festival's genre bias.
        for _ in range(history_n):
            genre = rng.choice(GENRES)
            selected = rng.random() < bias.get(genre, 0.08)
            festivals_svc.ingest_historical_selection(
                db, fest.id,
                genre=genre,
                runtime_minutes=rng.choice([8, 12, 15, 22, 28, 85, 95, 110]),
                year=rng.randint(today.year - 4, today.year - 1),
                selected=selected,
            )

        db.add(DiscountCode(
            festival_id=fest.id, code="EARLYBIRD", kind=DiscountKind.PERCENT,
            amount=20, valid_to=today + timedelta(days=20), redemption_limit=100,
            label="Launch promotion",
        ))
        if i == 0:
            db.add(DiscountCode(
                festival_id=fest.id, code="OUTREACH2026",
                code_type=CodeType.FEE_WAIVER, label="Community outreach program",
                one_use_per_submitter=True,
            ))
            db.add(DiscountCode(
                festival_id=fest.id, code="LATEPASS",
                code_type=CodeType.DEADLINE_WAIVER, label="Programmer-invited late entries",
                redemption_limit=10, one_use_per_submitter=True,
            ))

    priya = accounts.register_user(
        db, "priya@example.com", "reelfit-demo", "Priya Sharma", UserKind.FILMMAKER
    )
    priya.credit_balance = 3
    priya.bio = (
        "Priya Sharma is an independent documentary filmmaker from Kolkata. "
        "Her short-form work focuses on the people who keep small towns "
        "running. Monsoon Letters is her second film."
    )
    monsoon = accounts.create_film(
        db, priya.id, "Monsoon Letters", "documentary", 24, today.year - 1,
        logline="Three postal workers keep a flooded town connected.",
        country="India",
        synopsis=(
            "When the monsoon cuts the town of Alipurduar off for six weeks "
            "each year, its three postal workers become the only thread "
            "between families. Shot over two flood seasons, Monsoon Letters "
            "follows their routes by boat, bicycle and memory."
        ),
        language="Bengali (English subtitles)",
        credits="Priya Sharma — Director\nArun Bose — Cinematographer\nMeera Iyer — Editor\nRahul Sen — Sound",
        screener_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        first_time_filmmaker=False,
        student_project=False,
    )
    glass = accounts.create_film(
        db, priya.id, "Glass Houses", "drama", 96, today.year - 1,
        logline="A family reunion unravels over one weekend.",
        country="India",
        synopsis=(
            "Three siblings return to their childhood home to settle their "
            "mother's estate. Over one monsoon weekend, the house gives up "
            "its secrets one room at a time."
        ),
        language="Hindi (English subtitles)",
        credits="Priya Sharma — Director\nVikram Rao — Producer\nSana Qureshi — Editor",
        screener_url="https://vimeo.com/76979871",
    )
    accounts.create_film(db, priya.id, "The Last Projectionist", "drama", None,
                         today.year, kind=ProjectKind.SCREENPLAY,
                         logline="A dying cinema's projectionist refuses to go digital.",
                         country="India")

    organizer = accounts.register_user(
        db, "organizer@example.com", "reelfit-demo", "Arjun Mehta", UserKind.ORGANIZER
    )
    db.add(FestivalMembership(
        user_id=organizer.id, festival_id=fests[0].id, role=OrgRole.OWNER
    ))
    juror = accounts.register_user(
        db, "jury@example.com", "reelfit-demo", "Divya Kapoor", UserKind.ORGANIZER
    )
    db.add(FestivalMembership(
        user_id=juror.id, festival_id=fests[0].id, role=OrgRole.JURY
    ))
    db.commit()

    # Judging rubric for the founder's festival (BRD §5.1.3).
    from app.modules.jury import service as jury_svc

    criteria = {
        name: jury_svc.add_criterion(db, fests[0].id, name, weight)
        for name, weight in (
            ("Storytelling", 2.0), ("Craft", 1.0),
            ("Originality", 1.0), ("Festival fit", 1.0),
        )
    }

    # Demo submissions to the founder's festival so the submissions manager
    # has content: one under review, one selected.
    from app.modules.submissions import service as submissions_svc
    from app.modules.submissions.models import SubmissionStatus

    hillside = fests[0]
    for film, category_name, status in (
        (monsoon, "Documentary", SubmissionStatus.SELECTED),
        (glass, "Feature Film", SubmissionStatus.IN_REVIEW),
    ):
        edition = festivals_svc.current_edition(db, hillside.id)
        category = next(
            c for c in festivals_svc.categories_for_edition(db, edition.id)
            if c.name == category_name
        )
        sub = submissions_svc.create_submission(
            db, filmmaker_id=priya.id, film_id=film.id, film_kind=film.kind.value,
            film_runtime=film.runtime_minutes, film_year=film.year,
            film_title=film.title, festival_id=hillside.id, category_id=category.id,
            cover_letter=(
                f"Thank you for considering “{film.title}”. We'd love to "
                "screen at Hillside — the festival's documentary focus is "
                "exactly the audience this film was made for."
            ),
        )
        if status != SubmissionStatus.RECEIVED:
            submissions_svc.update_status(db, sub.id, status, actor_user_id=organizer.id)

        # Assign Divya to judge every entry; she has scored the first one.
        assignment = jury_svc.assign(db, sub.id, juror.id)
        if film is monsoon:
            jury_svc.record_scores(db, assignment.id, {
                criteria["Storytelling"].id: 9,
                criteria["Craft"].id: 8,
                criteria["Originality"].id: 8,
                criteria["Festival fit"].id: 9,
            })

    print(f"Seeded {len(fests)} festivals and 3 demo accounts (password: reelfit-demo).")


if __name__ == "__main__":
    seed()
