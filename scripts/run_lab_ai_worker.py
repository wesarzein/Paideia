"""Guarded one-off worker invocation in the existing synthetic laboratory."""

import argparse
import subprocess
from uuid import UUID

from verify_academic_lab_api import COMPOSE, guard_host
from verify_academic_ui import free_memory


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_id", type=UUID)
    args = parser.parse_args()
    guard_host()
    assert free_memory() >= 1536 * 1024**2, "Insufficient host RAM for training"
    code = (
        "from sqlalchemy.engine import make_url; from sqlalchemy import text; "
        "from app.core.config import settings; from app.core.database import engine; "
        "u=make_url(settings.database_url); assert (u.host,u.database,u.username)=="
        "('postgres','paideia_dev_phase4b3ui','paideia_dev'); "
        "c=engine.connect(); assert c.execute(text('SELECT current_database(),current_user')).one()=="
        "('paideia_dev_phase4b3ui','paideia_dev'); c.close(); "
        "from app.ai_worker import execute; from uuid import UUID; "
        f"execute(UUID('{args.run_id}'))"
    )
    subprocess.run(
        [
            *COMPOSE,
            "run",
            "--rm",
            "-T",
            "--no-deps",
            "--entrypoint",
            "python",
            "migrate",
            "-B",
            "-c",
            code,
        ],
        check=True,
    )


if __name__ == "__main__":
    main()
