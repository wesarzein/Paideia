"""Local, synthetic-trained projections. Never writes grades or institutional alerts."""

import hashlib
import json
import math
import random
from calendar import monthrange
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

from app.services.academic_metrics import academic_metrics

FEATURES = (
    "last_score",
    "trend",
    "mean_score",
    "variation",
    "history_count",
    "attendance_rate",
    "attendance_missing",
)
MODEL_PATH = Path(__file__).parents[1] / "assets" / "performance-forecast-v1.json"


def features(scores, attendance):
    mean = sum(scores) / len(scores)
    return [
        scores[-1],
        scores[-1] - scores[-2],
        mean,
        math.sqrt(sum((s - mean) ** 2 for s in scores) / len(scores)),
        len(scores),
        sum(r.status == "PRESENT" for r in attendance) / len(attendance) if attendance else 0,
        int(not attendance),
    ]


def observed_history(grades, periods, horizon, as_of, through_bimester=None, target_period_id=None):
    """Separate evaluation dates from explicitly completed bimesters; preserve weights."""
    grouped = defaultdict(list)
    period_map = {p.id: p for p in periods}
    excluded = 0
    for row in grades:
        period = period_map[row.period_id]
        generated = getattr(row, "created_at", None)
        if getattr(row, "data_origin", None) == "synthetic" and generated:
            generated_day = (
                generated.astimezone(ZoneInfo("America/Lima")).date()
                if generated.tzinfo
                else generated.date()
            )
            if generated_day > as_of:
                excluded += 1
                continue
        month = getattr(row, "academic_month", None)
        if month:
            from datetime import date

            if (
                date(period.starts_on.year, month, monthrange(period.starts_on.year, month)[1])
                > as_of
            ):
                excluded += 1
                continue
        if period.starts_on > as_of or (row.assessment_date and row.assessment_date > as_of):
            excluded += 1
            continue
        if horizon == "exam":
            if row.record_kind != "evaluation" or row.assessment_date is None:
                excluded += 1
                continue
            key = (row.assessment_date, str(row.period_id))
        else:
            if row.academic_bimester is None or (
                (period.id == target_period_id or period.ends_on > as_of)
                and row.academic_bimester > through_bimester
            ):
                excluded += 1
                continue
            key = (period.starts_on, str(period.id), row.academic_bimester)
        grouped[key].append(row)
    history = []
    for _key, rows in sorted(grouped.items()):
        metric = academic_metrics(rows, [])
        if metric.average_score is None:
            continue
        first = rows[0]
        history.append(
            {
                "label": str(first.assessment_date)
                if horizon == "exam"
                else f"{period_map[first.period_id].name} · Bimestre {first.academic_bimester}",
                "score": round(metric.average_score, 4),
                "records": len(rows),
                "period_id": str(first.period_id),
                "bimester": first.academic_bimester,
            }
        )
    return history, excluded


def synthetic_examples(seed=20261014, pupils=600):
    """Independent fictional trajectories; no reads from the academic database."""
    rng = random.Random(seed)
    examples = {"exam": [], "bimester": []}
    for pupil in range(pupils):
        # Fixed disjoint student cohorts, with targets advancing in time.
        split = "train" if pupil % 5 < 3 else "validation" if pupil % 5 == 3 else "test"
        for horizon in examples:
            for course in range(3):
                ability, slope = rng.uniform(3, 18), rng.uniform(-0.65, 0.65)
                presence = rng.uniform(0.45, 1)
                scores = []
                for index in range(12):
                    noise = rng.gauss(0, 1.8 if horizon == "exam" else 0.85)
                    score = max(0, min(20, ability + slope * index + noise))
                    allowed = (
                        (split == "train" and 3 <= index <= 7)
                        or (split == "validation" and index == 9)
                        or (split == "test" and index == 11)
                    )
                    if allowed:
                        from types import SimpleNamespace

                        attendance = [
                            SimpleNamespace(
                                status="PRESENT" if rng.random() < presence else "ABSENT"
                            )
                            for _ in range(20)
                        ]
                        if rng.random() < 0.25:
                            attendance = []
                        examples[horizon].append(
                            {
                                "student": pupil,
                                "course": course,
                                "target_index": index,
                                "split": split,
                                "features": features(scores, attendance),
                                "target": score,
                            }
                        )
                    scores.append(score)
    return examples


def train_forecast(seed=20261014, pupils=600):
    """Fit on training only; calibrate range on validation; report untouched test."""
    import numpy as np
    from sklearn.linear_model import Ridge
    from sklearn.metrics import mean_absolute_error, mean_squared_error
    from sklearn.preprocessing import StandardScaler
    from threadpoolctl import threadpool_limits

    dataset = synthetic_examples(seed, pupils)
    result = {
        "schema_version": 1,
        "source": "synthetic",
        "features": list(FEATURES),
        "seed": seed,
        "pupils": pupils,
        "horizons": {},
    }
    for horizon, rows in dataset.items():
        splits = {s: [r for r in rows if r["split"] == s] for s in ("train", "validation", "test")}
        scaler = StandardScaler().fit([r["features"] for r in splits["train"]])
        model = Ridge(alpha=10)
        with threadpool_limits(limits=1):
            model.fit(
                scaler.transform([r["features"] for r in splits["train"]]),
                [r["target"] for r in splits["train"]],
            )

        def predict(split, model=model, scaler=scaler, splits=splits):
            return np.clip(
                model.predict(scaler.transform([r["features"] for r in splits[split]])), 0, 20
            )

        residuals = sorted(
            abs(r["target"] - p)
            for r, p in zip(splits["validation"], predict("validation"), strict=True)
        )
        radius = residuals[min(len(residuals) - 1, math.ceil((len(residuals) + 1) * 0.9) - 1)]
        actual = np.array([r["target"] for r in splits["test"]])
        predicted = predict("test")
        baseline = [r["features"][0] for r in splits["test"]]
        result["horizons"][horizon] = {
            "mean": scaler.mean_.tolist(),
            "scale": scaler.scale_.tolist(),
            "coefficients": model.coef_.tolist(),
            "intercept": float(model.intercept_),
            "interval_radius": float(radius),
            "metrics": {
                "mae": float(mean_absolute_error(actual, predicted)),
                "rmse": float(math.sqrt(mean_squared_error(actual, predicted))),
                "baseline_mae": float(mean_absolute_error(actual, baseline)),
                "interval_coverage": float(np.mean(abs(actual - predicted) <= radius)),
            },
            "split": {
                s: {
                    "examples": len(rs),
                    "students": len({r["student"] for r in rs}),
                    "target_indices": sorted({r["target_index"] for r in rs}),
                }
                for s, rs in splits.items()
            },
        }
    result["dataset_sha256"] = hashlib.sha256(
        json.dumps(dataset, sort_keys=True).encode()
    ).hexdigest()
    result["version"] = "synthetic-ridge-v1-" + result["dataset_sha256"][:12]
    return result


@lru_cache(maxsize=1)
def load_model():
    model = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
    if (
        model["source"] != "synthetic"
        or model["features"] != list(FEATURES)
        or model["schema_version"] != 1
    ):
        raise ValueError("Unsupported forecast artifact")
    for horizon in ("exam", "bimester"):
        artifact = model["horizons"][horizon]
        for field in ("mean", "scale", "coefficients"):
            if len(artifact[field]) != len(FEATURES) or not all(
                isinstance(v, int | float) and math.isfinite(v) for v in artifact[field]
            ):
                raise ValueError("Invalid numerical forecast artifact")
        if (
            not all(v > 0 for v in artifact["scale"])
            or not math.isfinite(artifact["intercept"])
            or not 0 <= artifact["interval_radius"] <= 20
        ):
            raise ValueError("Invalid forecast scale or range")
    return model


def project(history, attendance, horizon, model):
    if len(history) < 3:
        return {
            "status": "insufficient_history",
            "score": None,
            "range": None,
            "trend": None,
            "factors": [],
            "recommendations": [
                "Registra al menos tres evaluaciones fechadas o tres bimestres completos del curso."
            ],
        }
    values = features([r["score"] for r in history], attendance)
    artifact = model["horizons"][horizon]
    contributions = [
        (v - m) / s * c
        for v, m, s, c in zip(
            values, artifact["mean"], artifact["scale"], artifact["coefficients"], strict=True
        )
    ]
    score = max(0, min(20, artifact["intercept"] + sum(contributions)))
    if not math.isfinite(score):
        raise ValueError("Invalid forecast")
    radius = artifact["interval_radius"]
    trend = "improving" if values[1] > 0.5 else "declining" if values[1] < -0.5 else "stable"
    recommendations = ["Revisa las competencias y criterios con menor desempeño en Analítica."]
    if trend == "declining":
        recommendations.append(
            "Contrasta la caída reciente con el docente y registra acompañamiento."
        )
    if not attendance:
        recommendations.append("Completa la asistencia para contextualizar el análisis.")
    elif values[5] < 0.7:
        recommendations.append("Revisa las ausencias registradas con el equipo académico.")
    return {
        "status": "experimental",
        "score": round(score, 2),
        "range": [round(max(0, score - radius), 2), round(min(20, score + radius), 2)],
        "trend": trend,
        "factors": [
            {
                "feature": FEATURES[i],
                "value": round(values[i], 3),
                "association": round(contributions[i], 3),
            }
            for i in sorted(range(len(values)), key=lambda i: abs(contributions[i]), reverse=True)[
                :3
            ]
        ],
        "recommendations": recommendations,
    }
