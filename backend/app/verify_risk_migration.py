"""Explicit lab-only 0016 upgrade, preserving fingerprints of every existing table."""

import json

from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import make_url

from app.core.config import settings
from app.core.database import engine
from app.inspect_database import inventory


def main():
    url = make_url(settings.database_url)
    assert (url.host, url.database, url.username) == (
        "postgres",
        "paideia_dev_phase4b3ui",
        "paideia_dev",
    )
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT current_database(),current_user,current_schema()")
        ).one() == ("paideia_dev_phase4b3ui", "paideia_dev", "public")
        assert (
            connection.scalar(text("SELECT version_num FROM alembic_version"))
            == "0015_user_account_status"
        )
    before = inventory()["tables"]
    assert before["grade_records"]["count"] == 32
    command.upgrade(Config("alembic.ini"), "0016_local_risk_models")
    after = inventory()["tables"]
    assert all(after[name] == value for name, value in before.items() if name != "alembic_version")
    assert set(after) - set(before) == {
        "risk_model_runs",
        "risk_model_deployments",
        "risk_model_events",
    }
    assert after["risk_model_runs"]["count"] == 0
    assert after["risk_model_deployments"]["count"] == 2
    print(
        json.dumps(
            {
                "passed": True,
                "revision": "0016_local_risk_models",
                "preserved_tables": len(before) - 1,
                "grade_count": 32,
                "grade_fingerprint": after["grade_records"]["fingerprint"],
            }
        )
    )


if __name__ == "__main__":
    main()
