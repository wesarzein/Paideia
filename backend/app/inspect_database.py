"""Read-only PostgreSQL inventory and row fingerprints; never initializes the app."""

import hashlib
import json

from sqlalchemy import UniqueConstraint, inspect, text

from app.core.database import engine
from app.models.base import Base


def inventory() -> dict:
    if engine.dialect.name != "postgresql":
        raise RuntimeError("This inspection requires PostgreSQL")
    result = {"tables": {}, "model_differences": []}
    with engine.connect() as connection, connection.begin():
        connection.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
        result["read_only"] = connection.scalar(text("SHOW transaction_read_only"))
        inspector = inspect(connection)
        quote = connection.dialect.identifier_preparer.quote
        tables = inspector.get_table_names(schema="public")
        for name in sorted(tables):
            qualified = f"{quote('public')}.{quote(name)}"
            count, fingerprint = connection.execute(
                text(
                    "SELECT count(*), md5(coalesce(string_agg(md5(row_to_json(t)::text), "
                    f"'' ORDER BY md5(row_to_json(t)::text)), '')) FROM {qualified} t"
                )
            ).one()
            columns = inspector.get_columns(name, schema="public")
            schema = [
                {"name": col["name"], "type": str(col["type"]), "nullable": col["nullable"]}
                for col in columns
            ]
            result["tables"][name] = {
                "count": count,
                "fingerprint": fingerprint,
                "schema_sha256": hashlib.sha256(
                    json.dumps(schema, sort_keys=True).encode()
                ).hexdigest(),
            }
            model = Base.metadata.tables.get(name)
            foreign_keys = inspector.get_foreign_keys(name, schema="public")
            if model is not None:
                actual = {col["name"]: col for col in columns}
                for col in model.columns:
                    if col.name not in actual:
                        result["model_differences"].append(f"{name}.{col.name}: missing")
                    elif col.nullable != actual[col.name]["nullable"]:
                        result["model_differences"].append(f"{name}.{col.name}: nullable differs")
                    elif col.type._type_affinity != actual[col.name]["type"]._type_affinity:
                        result["model_differences"].append(f"{name}.{col.name}: type differs")
                for extra in actual.keys() - {col.name for col in model.columns}:
                    result["model_differences"].append(f"{name}.{extra}: extra")
                actual_pk = inspector.get_pk_constraint(name, schema="public")[
                    "constrained_columns"
                ]
                if list(model.primary_key.columns.keys()) != actual_pk:
                    result["model_differences"].append(f"{name}: primary key differs")
                actual_unique = {
                    tuple(item["column_names"])
                    for item in inspector.get_unique_constraints(name, schema="public")
                }
                actual_unique.update(
                    tuple(item["column_names"])
                    for item in inspector.get_indexes(name, schema="public")
                    if item["unique"]
                )
                for constraint in model.constraints:
                    if isinstance(constraint, UniqueConstraint):
                        if tuple(constraint.columns.keys()) not in actual_unique:
                            result["model_differences"].append(f"{name}: unique constraint missing")
                actual_fk = {
                    (
                        tuple(fk["constrained_columns"]),
                        fk["referred_table"],
                        tuple(fk["referred_columns"]),
                    )
                    for fk in foreign_keys
                }
                for constraint in model.foreign_key_constraints:
                    elements = list(constraint.elements)
                    expected = (
                        tuple(element.parent.name for element in elements),
                        elements[0].column.table.name,
                        tuple(element.column.name for element in elements),
                    )
                    if expected not in actual_fk:
                        result["model_differences"].append(f"{name}: foreign key missing")
            for foreign_key in foreign_keys:
                parent_schema = quote(foreign_key["referred_schema"] or "public")
                parent = f"{parent_schema}.{quote(foreign_key['referred_table'])}"
                pairs = zip(
                    foreign_key["constrained_columns"], foreign_key["referred_columns"], strict=True
                )
                join = " AND ".join(f"c.{quote(c)} = p.{quote(p)}" for c, p in pairs)
                nonnull = " AND ".join(
                    f"c.{quote(c)} IS NOT NULL" for c in foreign_key["constrained_columns"]
                )
                orphans = connection.scalar(
                    text(
                        f"SELECT count(*) FROM {qualified} c WHERE {nonnull} "
                        f"AND NOT EXISTS (SELECT 1 FROM {parent} p WHERE {join})"
                    )
                )
                result["tables"][name].setdefault("foreign_key_orphans", {})[
                    foreign_key["name"]
                ] = orphans
        result["missing_model_tables"] = sorted(set(Base.metadata.tables) - set(tables))
        result["revision"] = (
            connection.scalar(text("SELECT version_num FROM alembic_version"))
            if "alembic_version" in tables
            else None
        )
        result["invalid_constraints"] = connection.scalar(
            text(
                "SELECT count(*) FROM pg_constraint "
                "WHERE connamespace = 'public'::regnamespace AND NOT convalidated"
            )
        )
    return result


def main() -> None:
    try:
        print(json.dumps(inventory(), sort_keys=True))
    except Exception:
        # Connection errors can include credentials; do not expose the exception.
        raise SystemExit("Inspección fallida; revise conexión y esquema de forma privada") from None


if __name__ == "__main__":
    main()
