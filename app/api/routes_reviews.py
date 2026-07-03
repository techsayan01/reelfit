from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import DbDep, FilmmakerDep
from app.api.routes_submissions import own_submission
from app.modules.reviews import service as reviews
from app.modules.reviews.service import ReviewError

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


class ReviewIn(BaseModel):
    submission_id: int
    rating: int = Field(ge=1, le=5)
    text: str = ""


@router.post("", status_code=201)
def create_review(db: DbDep, user: FilmmakerDep, body: ReviewIn):
    sub = own_submission(db, user, body.submission_id)
    try:
        review = reviews.create_review(
            db,
            submission_id=sub.id,
            festival_id=sub.festival_id,
            filmmaker_id=user.id,
            rating=body.rating,
            text=body.text,
        )
    except ReviewError as exc:
        raise HTTPException(400, str(exc))
    return {"review": {"id": review.id}}
