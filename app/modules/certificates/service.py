"""Certificates service: automated laurel generation for selected films.

Phase 1 renders an SVG laurel on demand from a template; the Certificate row
records that one was issued. Production moves rendered assets to object
storage via a Celery job without changing this interface.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.certificates.models import Certificate

_LAUREL_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 480 200" font-family="Georgia, serif">
  <g fill="none" stroke="{ink}" stroke-width="3">
    <path d="M70 160 C 30 130, 25 70, 60 35" />
    <path d="M410 160 C 450 130, 455 70, 420 35" />
  </g>
  <g fill="{ink}">
    {leaves_left}
    {leaves_right}
  </g>
  <text x="240" y="78" text-anchor="middle" font-size="20" fill="{ink}">{headline}</text>
  <text x="240" y="112" text-anchor="middle" font-size="26" font-style="italic" fill="#B8791A">{festival_name}</text>
  <text x="240" y="142" text-anchor="middle" font-size="16" fill="{muted}">{edition_label}</text>
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


def _esc(text: str) -> str:
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_laurel_svg(
    festival_name: str,
    edition_label: str,
    headline: str = "OFFICIAL SELECTION",
    variant: str = "black",
) -> str:
    """Laurel graphic; black variant for light backgrounds, white for dark."""
    ink = "#FFFFFF" if variant == "white" else "#1C1917"
    muted = "#D8D2C7" if variant == "white" else "#6B6560"
    return _LAUREL_SVG.format(
        festival_name=_esc(festival_name),
        edition_label=_esc(edition_label),
        headline=_esc(headline.upper()[:40]),
        ink=ink,
        muted=muted,
        leaves_left=_leaves("left"),
        leaves_right=_leaves("right"),
    )


_AD_BACKGROUNDS = {
    "amber": ("#B8791A", "#1C1917"),
    "ink": ("#1C1917", "#3F5C5E"),
    "teal": ("#3F5C5E", "#1C1917"),
}


def render_ad_svg(
    festival_name: str,
    headline: str,
    subline: str = "",
    cta: str = "Submit now",
    background: str = "amber",
    fmt: str = "square",
) -> str:
    """Social ad graphic (ad creator): Instagram square or Facebook/X wide,
    in Reelfit's film-world palette."""
    width, height = (1080, 1080) if fmt == "square" else (1200, 630)
    c1, c2 = _AD_BACKGROUNDS.get(background, _AD_BACKGROUNDS["amber"])
    cy = height / 2
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" font-family="Georgia, serif">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{c1}"/>
      <stop offset="1" stop-color="{c2}"/>
    </linearGradient>
  </defs>
  <rect width="{width}" height="{height}" fill="url(#bg)"/>
  <circle cx="{width - 90}" cy="90" r="46" fill="none" stroke="#FAF7F2" stroke-width="5" opacity="0.7"/>
  <circle cx="{width - 90}" cy="90" r="30" fill="#FAF7F2" opacity="0.25"/>
  <text x="{width / 2}" y="{cy - 120}" text-anchor="middle" font-size="34" fill="#FAF7F2" opacity="0.85"
        font-family="Helvetica, Arial, sans-serif" letter-spacing="4">{_esc(festival_name.upper()[:48])}</text>
  <text x="{width / 2}" y="{cy}" text-anchor="middle" font-size="84" font-weight="bold" fill="#FAF7F2">{_esc(headline[:36])}</text>
  <text x="{width / 2}" y="{cy + 70}" text-anchor="middle" font-size="42" fill="#FAF7F2" opacity="0.9">{_esc(subline[:56])}</text>
  <g transform="translate({width / 2}, {cy + 150})">
    <rect x="-160" y="-38" width="320" height="76" rx="38" fill="#FAF7F2"/>
    <text x="0" y="12" text-anchor="middle" font-size="34" fill="#1C1917"
          font-family="Helvetica, Arial, sans-serif">{_esc(cta[:22])}</text>
  </g>
  <text x="{width / 2}" y="{height - 46}" text-anchor="middle" font-size="26" fill="#FAF7F2" opacity="0.7"
        font-family="Helvetica, Arial, sans-serif">Reelfit. — see where your film fits</text>
</svg>"""


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
