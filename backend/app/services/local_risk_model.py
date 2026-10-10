"""Experimental logistic regression; artifacts contain numbers, never executable pickle."""

import hashlib
import json
import math

from app.services.risk_features import FEATURE_NAMES


def train_candidate(examples, seed=42):
    # Imports stay in the on-demand training process, outside normal API startup.
    import numpy as np
    import pandas as pd
    import sklearn
    from sklearn.dummy import DummyClassifier
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import brier_score_loss, confusion_matrix, precision_recall_fscore_support
    from sklearn.preprocessing import StandardScaler
    from threadpoolctl import threadpool_limits

    usable = [r for r in examples if r["status"] == "ready" and r.get("target") is not None]
    if len(usable) < 80:
        raise ValueError("Insufficient labeled examples (experimental minimum: 80)")
    latest = max(r["target_index"] for r in usable)

    def held_out(student_id):
        return int(hashlib.sha256(f"{seed}:{student_id}".encode()).hexdigest(), 16) % 5 == 0

    train = [r for r in usable if r["target_index"] < latest and not held_out(r["student_id"])]
    test = [r for r in usable if r["target_index"] == latest and held_out(r["student_id"])]
    if len(train) < 40 or len(test) < 20:
        raise ValueError("Insufficient temporal/student holdout")
    y_train, y_test = [r["target"] for r in train], [r["target"] for r in test]
    train_students = {r["student_id"] for r in train}
    test_students = {r["student_id"] for r in test}
    if train_students & test_students:
        raise ValueError("Student leakage between training and evaluation")
    if set(y_train) != {0, 1} or set(y_test) != {0, 1}:
        raise ValueError("Both classes are required in training and evaluation")
    x_train = pd.DataFrame([r["features"] for r in train], columns=FEATURE_NAMES, dtype=float)
    x_test = pd.DataFrame([r["features"] for r in test], columns=FEATURE_NAMES, dtype=float)
    if x_train.isna().all().any():
        raise ValueError("A feature has no training evidence")
    imputer = SimpleImputer(strategy="median")
    scaler = StandardScaler()
    train_matrix = scaler.fit_transform(imputer.fit_transform(x_train))
    test_matrix = scaler.transform(imputer.transform(x_test))
    model = LogisticRegression(random_state=seed, max_iter=500, solver="lbfgs")
    with threadpool_limits(limits=1):
        model.fit(train_matrix, y_train)
    probabilities = model.predict_proba(test_matrix)[:, 1]
    prediction = model.predict(test_matrix)
    baseline = DummyClassifier(strategy="most_frequent").fit(train_matrix, y_train)

    def metrics(pred, proba):
        precision, recall, f1, _ = precision_recall_fscore_support(
            y_test, pred, average="binary", zero_division=0
        )
        return {
            "precision": float(precision),
            "recall": float(recall),
            "f1": float(f1),
            "confusion_matrix": confusion_matrix(y_test, pred, labels=[0, 1]).tolist(),
            "brier_score": float(brier_score_loss(y_test, proba)),
        }

    artifact = {
        "schema_version": 1,
        "features": list(FEATURE_NAMES),
        "imputation": imputer.statistics_.tolist(),
        "mean": scaler.mean_.tolist(),
        "scale": scaler.scale_.tolist(),
        "coefficients": model.coef_[0].tolist(),
        "intercept": float(model.intercept_[0]),
        "mode": "demonstration",
    }
    assert all(
        math.isfinite(n)
        for key in ("imputation", "mean", "scale", "coefficients")
        for n in artifact[key]
    )
    assert np.isfinite(probabilities).all()
    return {
        "artifact": artifact,
        "metrics": metrics(prediction, probabilities),
        "baseline": metrics(
            baseline.predict(test_matrix), baseline.predict_proba(test_matrix)[:, 1]
        ),
        "split": {
            "train_count": len(train),
            "test_count": len(test),
            "train_students": len(train_students),
            "test_students": len(test_students),
            "student_overlap": len(train_students & test_students),
            "latest_target_index": latest,
        },
        "data_sha256": hashlib.sha256(json.dumps(usable, sort_keys=True).encode()).hexdigest(),
        "parameters": {
            "seed": seed,
            "solver": "lbfgs",
            "max_iter": 500,
            "sklearn_version": sklearn.__version__,
        },
        "limitation": "Synthetic rule-generated outcomes; not evidence of institutional efficacy",
    }


def predict_demonstration(artifact, row):
    validate_artifact(artifact)
    if row["status"] != "ready":
        return {"status": "insufficient_history", "risk": None, "probability": None}
    contributions = []
    for i, value in enumerate(row["features"]):
        value = artifact["imputation"][i] if value is None else value
        term = (value - artifact["mean"][i]) / artifact["scale"][i] * artifact["coefficients"][i]
        if not math.isfinite(term):
            raise ValueError("Non-finite artifact or feature")
        contributions.append(term)
    logit = max(-700, min(700, artifact["intercept"] + sum(contributions)))
    probability = 1 / (1 + math.exp(-logit))
    return {
        "status": "experimental",
        "risk": "high"
        if probability >= artifact.get("high_probability", 0.7)
        else "medium"
        if probability >= artifact.get("medium_probability", 0.3)
        else "low",
        "probability": probability,
        "factors": [
            {"feature": FEATURE_NAMES[i], "association": v}
            for i, v in sorted(enumerate(contributions), key=lambda t: abs(t[1]), reverse=True)[:3]
        ],
        "warning": "Demonstration only; associations are not proven causes",
    }


def validate_artifact(artifact):
    if (
        artifact.get("mode") != "demonstration"
        or artifact.get("schema_version") != 1
        or artifact.get("features") != list(FEATURE_NAMES)
    ):
        raise ValueError("Unsupported artifact")
    for field in ("imputation", "mean", "scale", "coefficients"):
        values = artifact.get(field, [])
        if len(values) != len(FEATURE_NAMES) or not all(
            isinstance(v, int | float) and math.isfinite(v) for v in values
        ):
            raise ValueError("Invalid numerical artifact")
    if not all(v > 0 for v in artifact["scale"]) or not math.isfinite(
        artifact.get("intercept", float("nan"))
    ):
        raise ValueError("Invalid scale or intercept")
    if (
        not 0
        <= artifact.get("medium_probability", 0.3)
        < artifact.get("high_probability", 0.7)
        <= 1
    ):
        raise ValueError("Invalid risk probability thresholds")
