"""Authenticated transaction context for database-enforced academic history."""

import json

from sqlalchemy import event, text
from sqlalchemy.orm import Session


def apply_context(connection, actor):
    if connection.dialect.name == "postgresql":
        connection.execute(
            text(
                "SELECT set_config('paideia.actor_id', :id, true), "
                "set_config('paideia.actor_role', :role, true), "
                "set_config('paideia.authorization', :authorization, true)"
            ),
            actor,
        )


@event.listens_for(Session, "after_begin")
def transaction_actor(db, _transaction, connection):
    actor = db.info.get("academic_actor")
    if actor:
        apply_context(connection, actor)


def set_actor(db, user, authorization=None):
    actor = {
        "id": str(user.id),
        "role": user.role.code,
        "authorization": json.dumps(authorization) if authorization else "",
    }
    db.info["academic_actor"] = actor
    apply_context(db.connection(), actor)
