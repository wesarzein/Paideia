"""Privileged operator command. Preview by default; never runs migrations."""

import argparse
import hashlib
import json
from pathlib import Path

from app.core.database import SessionLocal
from app.services.school_roster import ROSTER_PATH, synchronize_roster


def main() -> None:
    parser = argparse.ArgumentParser(description="Importación aditiva del padrón privado")
    parser.add_argument("--path", type=Path, default=ROSTER_PATH)
    parser.add_argument("--apply", action="store_true", help="Confirma y guarda la transacción")
    parser.add_argument(
        "--update-existing",
        action="store_true",
        help="Permite actualizar nombres/grupo usando UUID o código estable",
    )
    parser.add_argument("--sha256", help="Huella de la vista previa; obligatoria al aplicar")
    args = parser.parse_args()
    try:
        content = args.path.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        if args.apply and args.sha256 != digest:
            parser.error("Para aplicar, use --sha256 con la huella de una vista previa actual")
        roster = json.loads(content)
        with SessionLocal() as db:
            try:
                counts = synchronize_roster(db, roster, update_existing=args.update_existing)
                if args.apply:
                    db.commit()
                else:
                    db.rollback()
            except Exception:
                db.rollback()
                raise
        print(json.dumps({"applied": args.apply, "sha256": digest, "changes": counts}))
    except Exception:
        # SQLAlchemy exceptions may contain names, SQL parameters or credentials.
        parser.exit(
            1,
            "Importación rechazada y revertida; revise estructura, identidades y esquema "
            "en un entorno privado.\n",
        )


if __name__ == "__main__":
    main()
