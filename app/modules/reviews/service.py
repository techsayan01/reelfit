"""Reviews service: submission-verified reviews with festival right-of-reply."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.reviews.models import Review


class ReviewError(Exception):
    pass


def create_review(
    db: Session,
    *,
    submission_id: int,
    festival_id: int,
    filmmaker_id: int,
    rating: int,
    text: str,
) -> Review:
    if not 1 <= rating <= 5:
        raise ReviewError("Rating must be between 1 and 5.")
    if db.scalar(select(Review).where(Review.submission_id == submission_id)):
        raise ReviewError("You've already reviewed this festival for that submission.")
    review = Review(
        submission_id=submission_id,
        festival_id=festival_id,
        filmmaker_id=filmmaker_id,
        rating=rating,
        text=text.strip(),
    )
    db.add(review)
    db.commit()
    return review


def reviews_for_festival(db: Session, festival_id: int) -> list[Review]:
    return list(
        db.scalars(
            select(Review)
            .where(Review.festival_id == festival_id)
            .order_by(Review.created_at.desc())
        )
    )


def reviewed_submission_ids(db: Session, filmmaker_id: int) -> set[int]:
    return {
        r.submission_id
        for r in db.scalars(select(Review).where(Review.filmmaker_id == filmmaker_id))
    }


def reply(db: Session, review_id: int, reply_text: str) -> Review:
    review = db.get(Review, review_id)
    if review is None:
        raise ReviewError("Review not found.")
    review.festival_reply = reply_text.strip()
    db.commit()
    return review
