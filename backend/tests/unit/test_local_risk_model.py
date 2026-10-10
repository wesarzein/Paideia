from copy import deepcopy

import pytest
from test_roster_persistence import sessions

from app.services.demonstration_dataset import labeled_examples, populate_demonstration
from app.services.local_risk_model import predict_demonstration, train_candidate

__all__ = ["sessions"]


def test_seeded_postgresql_history_train_evaluate_and_safe_infer(sessions):
    with sessions() as db:
        lineage = populate_demonstration(db)
        assert lineage["personal_data"] is False
        rows = labeled_examples(db)
        assert any(r["status"] == "insufficient_history" for r in rows)
        result = train_candidate(rows)
        repeated = train_candidate(rows)
        assert result == repeated
        assert result["split"]["student_overlap"] == 0
        assert result["split"]["test_count"] >= 20
        assert (
            sum(sum(r) for r in result["metrics"]["confusion_matrix"])
            == result["split"]["test_count"]
        )
        assert 0 <= result["metrics"]["f1"] <= 1
        ready = next(r for r in rows if r["status"] == "ready")
        pred = predict_demonstration(result["artifact"], ready)
        assert 0 <= pred["probability"] <= 1
        assert len(pred["factors"]) == 3
        unavailable = deepcopy(ready)
        unavailable["status"] = "insufficient_history"
        assert predict_demonstration(result["artifact"], unavailable)["risk"] is None
        institutional = deepcopy(result["artifact"])
        institutional["mode"] = "institutional"
        with pytest.raises(ValueError, match="Unsupported"):
            predict_demonstration(institutional, ready)
        with pytest.raises(ValueError, match="empty isolated"):
            populate_demonstration(db)


def test_training_rejects_insufficient_evidence():
    with pytest.raises(ValueError, match="Insufficient labeled"):
        train_candidate([])
