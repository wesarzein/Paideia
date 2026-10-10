"""Explicit, idempotent synthetic catalog; forbidden on institutional databases."""

import os
from pathlib import Path

from sqlalchemy.engine import make_url

from app.core.config import settings
from app.core.database import SessionLocal
from app.services.school_roster import load_roster, synchronize_roster


def ensure_development_target() -> None:
    url = make_url(settings.database_url)
    if (
        settings.environment != "development"
        or os.environ.get("ALLOW_SYNTHETIC_SEED") != "true"
        or url.username != "paideia_dev"
        or not (url.database or "").startswith("paideia_dev_")
    ):
        raise RuntimeError(
            "Seed permitido solo en una base paideia_dev_* explícitamente habilitada"
        )


def main() -> None:
    ensure_development_target()
    roster = load_roster(Path("/fixtures/roster.synthetic.json"))
    if roster is None:
        raise RuntimeError("No se encontró el catálogo sintético")
    with SessionLocal() as db, db.begin():
        counts = synchronize_roster(db, roster)
    print(counts)


if __name__ == "__main__":
    main()
