"""Certificates service: automated laurel generation for selected films.

Phase 1 renders an SVG laurel on demand from a template; the Certificate row
records that one was issued. Production moves rendered assets to object
storage via a Celery job without changing this interface.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.certificates.models import Certificate

_LAUREL_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 480 200" font-family="Georgia, serif">
  <g fill="none" stroke="#1C1917" stroke-width="3">
    <path d="M70 160 C 30 130, 25 70, 60 35" />
    <path d="M410 160 C 450 130, 455 70, 420 35" />
  </g>
  <g fill="#1C1917">
    {leaves_left}
    {leaves_right}
  </g>
  <text x="240" y="78" text-anchor="middle" font-size="20" fill="#1C1917">OFFICIAL SELECTION</text>
  <text x="240" y="112" text-anchor="middle" font-size="26" font-style="italic" fill="#B8791A">{festival_name}</text>
  <text x="240" y="142" text-anchor="middle" font-size="16" fill="#6B6560">{edition_label}</text>
</svg>"""


def _leaves(side: str) -> str:
    leaves = []
    for i in range(7):
        y = 150 - i * 18
        if side == "left":
            x, rot = 62 - (i % 3) * 6, -35 - i * 8
        else:
            x, rot = 418 + (i % 3) * 6, 35 + i * 8
        leaves.append(
            f'<ellipse cx="{x}" cy="{y}" rx="14" ry="5" '
            f'transform="rotate({rot} {x} {y})"/>'
        )
    return "\n    ".join(leaves)


def render_laurel_svg(festival_name: str, edition_label: str) -> str:
    return _LAUREL_SVG.format(
        festival_name=festival_name,
        edition_label=edition_label,
        leaves_left=_leaves("left"),
        leaves_right=_leaves("right"),
    )


def issue_certificate(db: Session, submission_id: int, template: str = "laurel-classic") -> Certificate:
    existing = db.scalar(
        select(Certificate).where(Certificate.submission_id == submission_id)
    )
    if existing:
        return existing
    cert = Certificate(submission_id=submission_id, template=template)
    db.add(cert)
    db.commit()
    return cert


def for_submission(db: Session, submission_id: int) -> Certificate | None:
    return db.scalar(select(Certificate).where(Certificate.submission_id == submission_id))
