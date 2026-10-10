"""HTTP academic audit against ONLY the synthetic phase4a environment.

Records expected-vs-observed behavior, including reproducible defects. No deletes,
no production target, no source workbook, no functional application changes.
Run once on a fresh migrated/seeded audit database.
"""

import csv
import json
import os
from datetime import date
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from openpyxl import load_workbook
from sqlalchemy.engine import make_url

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.base import AcademicPeriod, Section

url = make_url(settings.database_url)
assert settings.environment == "development"
assert url.database == "paideia_dev_phase4a" and url.username == "paideia_dev"
assert url.host == "postgres" and os.environ.get("ALLOW_SYNTHETIC_SEED") == "true"
ROOT = Path("/results")
BASE = "http://frontend:4200/api/v1"
results = []


def record(name, expected, observed, ok):
    results.append(
        dict(
            id=name,
            expected=expected,
            observed=observed,
            status="unverified" if ok is None else "verified" if ok else "defect",
        )
    )
    print(json.dumps(results[-1], ensure_ascii=True), flush=True)


def call(method, path, payload=None, token=None, file=None, filename=None, raw=False):
    headers = {}
    body = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if file is not None:
        boundary = "phase4a-synthetic-boundary"
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
        body = (
            (
                f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
                f'filename="{filename}"\r\n'
                "Content-Type: application/octet-stream\r\n\r\n"
            ).encode()
            + file
            + f"\r\n--{boundary}--\r\n".encode()
        )
    elif payload is not None:
        body = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    request = Request(BASE + path, data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=30) as response:
            content = response.read()
            return response.status, content if raw else json.loads(content) if content else None
    except HTTPError as error:
        content = error.read()
        if raw:
            return error.code, content
        try:
            value = json.loads(content) if content else None
        except ValueError:
            value = {"non_json_error": True}
        return error.code, value


def good(method, path, payload=None, token=None, **kwargs):
    status, value = call(method, path, payload, token, **kwargs)
    assert 200 <= status < 300, f"Audit setup/request failed: {method} {path} HTTP {status}"
    return value


def login(email, password):
    return good("POST", "/auth/login", dict(email=email, password=password))["access_token"]


admin = login(settings.initial_admin_email, settings.initial_admin_password)
catalog = good("GET", "/academic/catalog", token=admin)
grade_id = catalog["grades"][0]["id"]
section_id = catalog["sections"][0]["id"]
period_id = catalog["periods"][0]["id"]
course = next(c for c in catalog["courses"] if c["name"] == "Matemática")
course_id = course["id"]
other_course_id = next(c["id"] for c in catalog["courses"] if c["id"] != course_id)
existing_codes = {
    s["student_code"] for s in good("GET", f"/students?section_id={section_id}", token=admin)
}
for number in range(4, 17):
    if f"1SA{number:03d}" in existing_codes:
        continue
    good(
        "POST",
        "/students",
        dict(
            first_name=f"ALUMNO {number:03d}",
            last_name="SINTETICO",
            grade_id=grade_id,
            section_id=section_id,
        ),
        admin,
    )
students = good("GET", f"/students?section_id={section_id}", token=admin)
record(
    "API-01", "16 synthetic pupils with stable generated codes", len(students), len(students) == 16
)
student_id = next(s["id"] for s in students if s["student_code"] == "1SA001")
password = "SyntheticPhase4aOnly!2026"
users = {}
for role in ("teacher", "coordinator", "director", "student", "parent"):
    payload = dict(
        email=f"{role}@phase4a.example.com",
        password=password,
        full_name=f"Usuario sintetico {role}",
        role_code=role,
    )
    if role == "student":
        payload["student_id"] = student_id
    if role == "parent":
        payload["student_ids"] = [student_id]
    user = next(
        (u for u in good("GET", "/users", token=admin) if u["email"] == payload["email"]), None
    )
    if user is None:
        user = good("POST", "/users", payload, admin)
    users[role] = dict(id=user["id"], token=login(payload["email"], password))
good(
    "POST",
    f"/courses/{course_id}/assignments",
    dict(section_id=section_id, teacher_id=users["teacher"]["id"]),
    admin,
)
with SessionLocal() as db, db.begin():
    from uuid import UUID

    from sqlalchemy import select

    reserved_section = db.scalar(
        select(Section).where(Section.grade_id == UUID(grade_id), Section.name == "B")
    )
    if reserved_section is None:
        reserved_section = Section(grade_id=UUID(grade_id), name="B")
        db.add(reserved_section)
    db.flush()
    reserved_id = str(reserved_section.id)
if not good("GET", f"/students?section_id={reserved_id}", token=admin):
    good(
        "POST",
        "/students",
        dict(
            first_name="RESERVA", last_name="SINTETICO", grade_id=grade_id, section_id=reserved_id
        ),
        admin,
    )
status, _ = call("GET", "/users", token=users["teacher"]["token"])
record("API-02", "Teacher cannot list administrative user accounts", status, status == 403)
status, assigned = call("GET", "/courses", token=users["teacher"]["token"])
record(
    "API-03",
    "Teacher sees only assigned course",
    len(assigned),
    status == 200 and len(assigned) == 1,
)

for fixture in ("institucional-vacios.xlsx", "institucional-sintetico.xlsx"):
    status, preview = call(
        "POST",
        f"/imports/grades/preview?period_id={period_id}",
        token=admin,
        file=(ROOT / fixture).read_bytes(),
        filename=fixture,
    )
    if "vacios" in fixture:
        record(
            "EX-01",
            "Blank marks with formula cached zeros produce no grade rows",
            dict(http=status, rows=preview.get("total"), errors=len(preview.get("errors", []))),
            status == 200 and preview.get("total") == 0,
        )
    else:
        filled_preview = preview
        record(
            "EX-02",
            "Ten synthetic input marks; computed averages not imported",
            dict(http=status, rows=preview.get("total")),
            status == 200 and preview.get("total") == 10,
        )
        record(
            "EX-03",
            "Two blocks identified consistently without inventing calendar dates",
            dict(
                evaluation_names=sorted(set(r["evaluation_name"] for r in preview.get("rows", []))),
                missing_dates=sum(not r.get("assessment_date") for r in preview.get("rows", [])),
            ),
            set(r["evaluation_name"] for r in preview.get("rows", [])) == {"Mes 1", "Mes 2"}
            if status == 200
            else None,
        )
before = len(good("GET", "/grades", token=admin))
record("EX-04", "Previews do not persist grades", before, before == 0)
bad_csv = b"student_code,score,assessment_date,evaluation_type\n1SA001,99,2026-03-01,Cuaderno\n"
status, invalid_preview = call(
    "POST",
    f"/imports/grades/preview?period_id={period_id}",
    token=admin,
    file=bad_csv,
    filename="invalid.synthetic.csv",
)
record(
    "EX-05",
    "Out-of-range preview mark rejected",
    len(invalid_preview.get("errors", [])),
    status == 200 and len(invalid_preview.get("errors", [])) == 1,
)
unknown_csv = bad_csv.replace(b"1SA001,99", b"UNKNOWN-SYNTHETIC,15")
status, unknown_preview = call(
    "POST",
    f"/imports/grades/preview?period_id={period_id}",
    token=admin,
    file=unknown_csv,
    filename="unknown.synthetic.csv",
)
record(
    "EX-06",
    "Preview detects an unknown pupil before confirmation",
    len(unknown_preview.get("errors", [])),
    bool(unknown_preview.get("errors")),
)
if "rows" in filled_preview:
    rows = [
        dict(r, assessment_date="2026-03-01" if i < 5 else "2026-04-01")
        for i, r in enumerate(filled_preview["rows"])
    ]
else:
    # Continue independent persistence tests using an explicitly DIFFERENT flat CSV.
    # This is not evidence that the institutional XLSX works.
    types = ["Actitud ante el área", "Cuaderno", "Módulo", "Exposición-Trabajos", "Evaluación"]
    rows = [
        dict(
            student_code="1SA001",
            score=score,
            assessment_date="2026-03-01" if i < 5 else "2026-04-01",
            evaluation_type=types[i % 5],
            evaluation_name="Bloque sintetico 1" if i < 5 else "Bloque sintetico 2",
        )
        for i, score in enumerate([10, 12, 14, 16, 18, 20, 20, 20, 20, 20])
    ]
with (ROOT / "valid.synthetic.csv").open("w", encoding="utf-8", newline="") as output:
    writer = csv.DictWriter(output, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
payload = dict(course_id=course_id, period_id=period_id, rows=rows)
status, imported = call("POST", "/imports/grades/commit", payload, admin)
after = good("GET", "/grades", token=admin)
record(
    "EX-07",
    "Flat CSV explicitly confirmed persists ten marks on same pupil (not institutional XLSX)",
    dict(
        http=status, saved=len(after), same_pupil=all(r["student_id"] == student_id for r in after)
    ),
    status == 200 and len(after) == 10 and all(r["student_id"] == student_id for r in after),
)
status, _ = call("POST", "/imports/grades/commit", payload, admin)
after_repeat = good("GET", "/grades", token=admin)
record(
    "EX-08",
    "Reimport is idempotent (still ten marks)",
    dict(http=status, saved=len(after_repeat)),
    len(after_repeat) == 10,
)
failed = dict(
    payload, rows=[dict(rows[0], score=9), dict(rows[0], student_code="UNKNOWN-SYNTHETIC")]
)
status, _ = call("POST", "/imports/grades/commit", failed, admin)
record(
    "EX-09",
    "Failed mixed batch is rejected without partial inserts",
    dict(http=status, count=len(good("GET", "/grades", token=admin))),
    status == 422 and len(good("GET", "/grades", token=admin)) == len(after_repeat),
)
status, _ = call(
    "POST", "/imports/grades/commit", dict(payload, rows=[dict(rows[0], score="")]), admin
)
record("EX-10", "Blank mark is not persisted as zero by server", status, status == 422)
record(
    "EX-11",
    "Imported marks link to assessment components",
    sum(r["component_id"] is not None for r in after),
    all(r["component_id"] for r in after),
)

components = []
for name in ("Actitud ante el área", "Cuaderno", "Módulo", "Exposición-Trabajos", "Evaluación"):
    components.append(
        good(
            "POST", f"/courses/{course_id}/assessment-components", dict(name=name, weight=1), admin
        )
    )
status, _ = call(
    "POST", f"/courses/{course_id}/assessment-components", dict(name="Negativo", weight=-1), admin
)
record("EV-01", "Negative weight rejected", status, status == 422)
status, _ = call(
    "PATCH",
    f"/courses/{course_id}/assessment-components/{components[0]['id']}",
    dict(weight=2),
    users["teacher"]["token"],
)
record("EV-02", "Assigned authorized teacher can configure evaluation", status, status == 200)
created = []
for i, component in enumerate(components):
    created.append(
        good(
            "POST",
            "/grades",
            dict(
                student_id=student_id,
                course_id=course_id,
                period_id=period_id,
                component_id=component["id"],
                evaluation_type=component["name"],
                evaluation_name="Synthetic weighted check",
                assessment_date="2026-05-01",
                score=20 if i == 4 else 10,
            ),
            users["teacher"]["token"],
        )
    )
summary_path = (
    f"/grades/monthly-summary?grade_id={grade_id}&section_id={section_id}"
    f"&course_id={course_id}&period_id={period_id}&month=5"
)
avg_before = good("GET", summary_path, token=admin)["students"][0]["average"]
record("EV-03", "Weighted average with five equal weights = 12", avg_before, avg_before == 12)
good(
    "PATCH",
    f"/courses/{course_id}/assessment-components/{components[0]['id']}",
    dict(weight=3),
    admin,
)
avg_after = good("GET", summary_path, token=admin)["students"][0]["average"]
record(
    "EV-04",
    "Changing weights does not silently change historical results",
    dict(before=avg_before, after=avg_after),
    avg_before == avg_after,
)
record(
    "EV-05",
    "Configuration isolated to one course",
    len(good("GET", f"/courses/{other_course_id}/assessment-components", token=admin)),
    not good("GET", f"/courses/{other_course_id}/assessment-components", token=admin),
)
status, moved = call(
    "PATCH",
    f"/grades/{created[0]['id']}",
    dict(component_id="00000000-0000-0000-0000-000000000000"),
    admin,
)
record("EV-06", "Grade edit rejects invalid component cleanly", status, status == 422)
status, _ = call(
    "POST",
    "/grades",
    dict(
        student_id=student_id,
        course_id=course_id,
        period_id=period_id,
        evaluation_type="Cuaderno",
        assessment_date="2030-01-01",
        score=0,
    ),
    admin,
)
record("AC-01", "Manual entry rejects dates outside academic period", status, status == 422)
manual_zero = good(
    "POST",
    "/grades",
    dict(
        student_id=student_id,
        course_id=course_id,
        period_id=period_id,
        evaluation_type="Cuaderno",
        assessment_date="2026-06-01",
        score=0,
    ),
    admin,
)
record(
    "AC-02",
    "Explicit zero is preserved as a real manual mark",
    manual_zero["score"],
    manual_zero["score"] == 0,
)
good("PATCH", f"/grades/{manual_zero['id']}", dict(score=1), admin)
record(
    "AC-03",
    "Manual edit is readable by authorized second user",
    any(
        r["id"] == manual_zero["id"] and r["score"] == 1
        for r in good("GET", "/grades", token=users["teacher"]["token"])
    ),
    any(
        r["id"] == manual_zero["id"] and r["score"] == 1
        for r in good("GET", "/grades", token=users["teacher"]["token"])
    ),
)
attendance_payload = dict(
    student_id=student_id,
    course_id=course_id,
    period_id=period_id,
    attendance_date="2026-03-01",
    status="PRESENT",
)
a = good("POST", "/attendance", attendance_payload, users["teacher"]["token"])
b = good(
    "POST", "/attendance", dict(attendance_payload, status="ABSENT"), users["teacher"]["token"]
)
record("AC-04", "Same daily attendance updates one record", a["id"] == b["id"], a["id"] == b["id"])
status, _ = call(
    "POST",
    "/attendance",
    dict(attendance_payload, attendance_date="2026-03-02", status="UNRECOGNIZED"),
    admin,
)
record("AC-05", "Attendance rejects unknown status", status, status == 422)
follow = good(
    "POST",
    "/follow-ups",
    dict(student_id=student_id, action="Seguimiento ficticio de auditoria"),
    users["teacher"]["token"],
)
good("PATCH", f"/follow-ups/{follow['id']}", dict(status="CLOSED"), users["teacher"]["token"])
follow_preserved = any(
    r["id"] == follow["id"]
    and r["recorded_by_id"] == users["teacher"]["id"]
    and r["status"] == "CLOSED"
    for r in good("GET", "/follow-ups", token=admin)
)
record("AC-06", "Follow-up retains author and updated state", follow_preserved, follow_preserved)
for role in ("student", "parent"):
    visible = good("GET", "/grades", token=users[role]["token"])
    record(
        f"RB-{role}",
        "Family account sees only linked pupil",
        len(visible),
        all(r["student_id"] == student_id for r in visible),
    )
    status, _ = call(
        "POST",
        "/grades",
        dict(student_id=student_id, course_id=course_id, period_id=period_id, score=10),
        users[role]["token"],
    )
    record(f"RB-{role}-write", "Family account cannot write marks", status, status == 403)

with SessionLocal() as db, db.begin():
    future = AcademicPeriod(
        name="Año escolar 2027", starts_on=date(2027, 1, 1), ends_on=date(2027, 12, 31)
    )
    db.add(future)
    db.flush()
    future_id = str(future.id)
record(
    "AC-07",
    "Catalog exposes another persisted academic year",
    any(p["id"] == future_id for p in good("GET", "/academic/catalog", token=admin)["periods"]),
    any(p["id"] == future_id for p in good("GET", "/academic/catalog", token=admin)["periods"]),
)
status, export = call(
    "GET",
    f"/reports/export.xlsx?grade_id={grade_id}&section_id={section_id}&period_id={period_id}&course_id={course_id}&month=3",
    token=admin,
    raw=True,
)
export_book = load_workbook(BytesIO(export), data_only=True)
record(
    "RP-01",
    "Filtered XLSX report downloadable and readable",
    dict(http=status, rows=export_book.active.max_row),
    status == 200 and export_book.active.max_row > 1,
)
for role in ("coordinator", "director"):
    status, _ = call("GET", "/reports/students", token=users[role]["token"])
    record(f"RP-{role}", "Role with report navigation can read report API", status, status == 200)
status, summary = call("GET", "/reports/summary", token=users["teacher"]["token"])
record(
    "RB-summary",
    "Teacher report summary excludes pupils with no marks/assignment outside scope",
    dict(http=status, total_students=summary.get("total_students"), assigned_pupils=16),
    summary.get("total_students") == 16,
)

# Synthetic replay inputs only, kept privately for browser tests. No tokens/passwords saved.
(ROOT / "browser-context.json").write_text(
    json.dumps(
        dict(
            course_id=course_id,
            other_course_id=other_course_id,
            period_id=period_id,
            grade_id=grade_id,
            section_id=section_id,
            student_id=student_id,
            components=components,
        )
    ),
    encoding="utf-8",
)
(ROOT / "api-results.json").write_text(
    json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
)
print(json.dumps(dict(checks=len(results), defects=sum(r["status"] == "defect" for r in results))))
