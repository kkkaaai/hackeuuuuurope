import os
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import init_db


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    init_db()
    yield
    db_path = "./test_agentflow.db"
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture()
def client():
    return TestClient(app)
