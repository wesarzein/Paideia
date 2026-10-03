"""Run Alembic safely against fresh, versioned, and legacy databases."""

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from app.core.database import engine


def main() -> None:
    config = Config("alembic.ini")
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    version = None

    if "alembic_version" in tables:
        with engine.connect() as connection:
            version = connection.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).scalar()

    legacy_tables = {"roles", "grades", "students", "courses", "academic_periods"}
    if version is None and tables.intersection(legacy_tables):
        command.stamp(config, "0002_grade_evaluation_fields")

    command.upgrade(config, "head")


if __name__ == "__main__":
    main()