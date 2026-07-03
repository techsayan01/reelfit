from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.deps import DbDep, FilmmakerDep
from app.modules.payments import service as payments

router = APIRouter(prefix="/api/credits", tags=["credits"])

# Dev-mode packs; production swaps in Stripe Checkout behind the same
# payments service call.
PACKS = {
    "single": {"label": "Single check", "credits": 1, "price_cents": 1500},
    "trio": {"label": "3-pack", "credits": 3, "price_cents": 3900},
    "five": {"label": "5-pack", "credits": 5, "price_cents": 5900},
}


class BuyIn(BaseModel):
    pack: str


@router.get("/packs")
def packs():
    return {"packs": [{"id": k, **v} for k, v in PACKS.items()]}


@router.post("/buy")
def buy(db: DbDep, user: FilmmakerDep, body: BuyIn):
    pack = PACKS.get(body.pack)
    if pack is None:
        raise HTTPException(400, "Unknown pack")
    payments.purchase_credits(db, user.id, pack["credits"], pack["price_cents"])
    return {"ok": True, "credit_balance": user.credit_balance}
