import os

import pytest
from sqlalchemy import create_engine, text


TEST_DATABASE_URL = os.getenv("CHARTVISION_POSTGRES_TEST_URL")


@pytest.fixture(autouse=True)
def isolate_postgres_integration_test():
    """Start each real-PostgreSQL integration test with empty domain tables."""
    if TEST_DATABASE_URL is None:
        yield
        return

    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    try:
        with engine.begin() as connection:
            connection.execute(text("TRUNCATE TABLE sessions RESTART IDENTITY CASCADE"))
        yield
    finally:
        engine.dispose()
