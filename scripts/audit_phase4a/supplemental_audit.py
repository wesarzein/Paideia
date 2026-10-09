"""Targeted parser, permission, history and component integrity reproductions."""

import json
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from openpyxl import Workbook
from sqlalchemy.engine import make_url

from app.core.config import settings
from app.endpoints.imports import _flatten_grade_frame, _read_frame
from app.inspect_database import inventory

target = make_url(settings.database_url)
assert (
    target.database == "paideia_dev_phase4a"
    and target.username == "paideia_dev"
    and target.host == "postgres"
)
assert settings.environment == "development"
root = Path("/results")
context = json.loads((root / "browser-context.json").read_text())
base = "http://frontend:4200/api/v1"
results = []


def record(identifier, expected, observed, ok):
    results.append(
        dict(
            id=identifier,
            expected=expected,
            observed=observed,
            status="verified" if ok else "defect",
        )
    )
    print(json.dumps(results[-1], ensure_ascii=True), flush=True)


def call(method, path, payload=None, token=None, body=None, content_type=None):
    headers = {"Authorization": "Bearer " + token} if token else {}
    if payload is not None:
        body = json.dumps(payload).encode()
        content_type = "application/json"
    if content_type:
        headers["Content-Type"] = content_type
    try:
        with urlopen(
            Request(base + path, data=body, headers=headers, method=method), timeout=30
        ) as response:
            return response.status, json.load(response)
    except HTTPError as e:
        return e.code, None


admin = call(
    "POST",
    "/auth/login",
    dict(email=settings.initial_admin_email, password=settings.initial_admin_password),
)[1]["access_token"]
teacher = call(
    "POST",
    "/auth/login",
    dict(email="teacher@phase4a.example.com", password="SyntheticPhase4aOnly!2026"),
)[1]["access_token"]
frame = _read_frame("synthetic.xlsx", (root / "institucional-sintetico.xlsx").read_bytes())
duplicate_headers = list(frame.columns[frame.columns.duplicated()])
try:
    _flatten_grade_frame(frame)
    exception_type = None
except Exception as error:
    exception_type = type(error).__name__
record(
    "DX-01",
    "Institutional grouped headers remain unique when flattened",
    dict(duplicate_headers=duplicate_headers, exception_type=exception_type),
    not duplicate_headers and exception_type is None,
)

book = Workbook()
book.active.append(["student_code", "score", "assessment_date", "evaluation_type"])
book.active.append(["1SA001", 15, "2026-03-01", "Cuaderno"])
stream = BytesIO()
book.save(stream)
boundary = "supplemental-synthetic"
body = (
    (
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
        'filename="flat.synthetic.xlsx"\r\n'
        "Content-Type: application/octet-stream\r\n\r\n"
    ).encode()
    + stream.getvalue()
    + f"\r\n--{boundary}--\r\n".encode()
)
status, preview = call(
    "POST",
    f"/imports/grades/preview?period_id={context['period_id']}",
    token=admin,
    body=body,
    content_type=f"multipart/form-data; boundary={boundary}",
)
record(
    "DX-02",
    "Flat XLSX reader works (does not replace institutional layout test)",
    dict(http=status, rows=preview["total"] if preview else None),
    status == 200 and preview["total"] == 1,
)

status, report = call("GET", "/reports/students", token=admin)
empty = [row for row in report if row["average_score"] == 0]
record(
    "RP-nodata",
    "Missing evidence is displayed as unavailable rather than real zero/high risk",
    dict(
        no_mark_students=len(empty),
        marked_high_risk=sum(row["risk_level"] == "ALTO" for row in empty),
    ),
    not any(row["risk_level"] == "ALTO" for row in empty),
)

row = dict(
    student_id=context["student_id"],
    course_id=context["other_course_id"],
    period_id=context["period_id"],
    score=20,
    evaluation_type="Cuaderno",
    assessment_date="2026-03-04",
)
status, _ = call("POST", "/grades", row, admin)
assert status == 201
status, _ = call("POST", "/grades", row, teacher)
record("RB-write-other", "Teacher cannot write outside assigned course", status, status == 403)
teacher_rows = call("GET", "/grades", token=teacher)[1]
summary = call("GET", f"/grades/summary/{context['student_id']}", token=teacher)[1]
visible_pupil_rows = [r for r in teacher_rows if r["student_id"] == context["student_id"]]
record(
    "RB-grade-summary",
    "Teacher pupil summary uses only the teacher's authorized courses",
    dict(summary_count=summary["count"], authorized_count=len(visible_pupil_rows)),
    summary["count"] == len(visible_pupil_rows),
)

status, foreign = call(
    "POST",
    f"/courses/{context['other_course_id']}/assessment-components",
    dict(name="Componente ajeno sintetico", weight=10),
    admin,
)
assert status == 201
record_to_change = next(r for r in teacher_rows if r["component_id"] is not None)
status, changed = call(
    "PATCH", f"/grades/{record_to_change['id']}", dict(component_id=foreign["id"]), admin
)
record(
    "EV-foreign-component",
    "Grade update rejects component from a different course",
    status,
    status == 422,
)

components = call("GET", f"/courses/{context['course_id']}/assessment-components", token=admin)[1]
extra = next(c for c in components if c["name"] == "Criterio extra sintetico")
status, changed = call(
    "PATCH",
    f"/courses/{context['course_id']}/assessment-components/{extra['id']}",
    dict(name="Criterio renombrado sintetico", is_active=False),
    admin,
)
record(
    "EV-rename-deactivate",
    "API renames and deactivates an optional criterion without deleting it",
    dict(
        http=status,
        same_id=changed and changed["id"] == extra["id"],
        inactive=changed and not changed["is_active"],
    ),
    status == 200 and changed["id"] == extra["id"] and not changed["is_active"],
)
inspected = inventory()
record(
    "HI-01",
    "Academic changes write a trace to the existing audit log",
    dict(audit_rows=inspected["tables"]["audit_logs"]["count"]),
    inspected["tables"]["audit_logs"]["count"] > 0,
)
(root / "supplemental-results.json").write_text(
    json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
)
