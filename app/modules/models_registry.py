"""Imports every module's models so SQLAlchemy metadata is complete.

Used by db.create_all() and Alembic autogenerate. This is the only place
allowed to import models across module boundaries.
"""

from app.modules.accounts import models as accounts_models  # noqa: F401
from app.modules.festivals import models as festivals_models  # noqa: F401
from app.modules.discounts import models as discounts_models  # noqa: F401
from app.modules.jury import models as jury_models  # noqa: F401
from app.modules.submissions import models as submissions_models  # noqa: F401
from app.modules.scoring import models as scoring_models  # noqa: F401
from app.modules.reviews import models as reviews_models  # noqa: F401
from app.modules.payments import models as payments_models  # noqa: F401
from app.modules.certificates import models as certificates_models  # noqa: F401
from app.modules.notifications import models as notifications_models  # noqa: F401
