import os

os.environ["DATABASE_URL"] = "sqlite:///./test_reelfit.db"
os.environ["REELFIT_DEBUG"] = "1"

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db import Base, engine
from app.main import app


@pytest.fixture()
def client():
    from app.modules import models_registry  # noqa: F401

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)


def pytest_sessionfinish(session, exitstatus):
    Path("test_reelfit.db").unlink(missing_ok=True)
