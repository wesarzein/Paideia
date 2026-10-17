"""Administrator owns academic CRUD; teachers read assignments and manage grades."""

import pytest
from test_academic_authorization import scenario, sessions

from app.endpoints import cohorts, courses, imports, periods
from app.services.evaluation_configuration import institutional_template

__all__ = ["scenario", "sessions"]


@pytest.fixture
def policy_api(scenario):
    client, ids, actors, current = scenario
    for module, prefix in [
        (cohorts, "/academic"),
        (courses, "/courses"),
        (imports, "/imports"),
        (periods, "/periods"),
    ]:
        client.app.include_router(module.router, prefix=prefix)
    for role, actor in actors.items():
        actor.email = f"{role}@synthetic.invalid"
    return client, ids, actors, current


@pytest.mark.parametrize("role", ["teacher", "coordinator", "director", "student", "parent"])
def test_nonadmin_cannot_write_academic_catalog_or_import_pupils(policy_api, role):
    client, ids, actors, current = policy_api
    current["user"] = actors[role]
    course, student, period, section = (
        ids["courses"][0],
        ids["students"][0],
        ids["period"],
        ids["sections"][0],
    )
    operations = [
        ("post", "/courses", {"name": "Nuevo curso"}),
        ("patch", f"/courses/{course}", {"name": "Cambio"}),
        ("delete", f"/courses/{course}", None),
        (
            "post",
            f"/courses/{course}/assignments",
            {"section_id": section, "teacher_id": str(actors["teacher"].id)},
        ),
        ("delete", f"/courses/{course}/assignments/{student}", None),
        ("post", "/academic/grades", {"name": "2°", "level": "Secundaria"}),
        ("patch", f"/academic/grades/{ids['grade']}", {"name": "1° grado"}),
        ("post", "/academic/sections", {"grade_id": ids["grade"], "name": "D"}),
        (
            "post",
            "/periods",
            {"name": "Periodo", "starts_on": "2026-01-01", "ends_on": "2026-12-31"},
        ),
        ("patch", f"/periods/{period}", {"name": "Cambio"}),
        (
            "post",
            "/students",
            {
                "first_name": "Alumno",
                "last_name": "Sintético",
                "grade_id": ids["grade"],
                "section_id": section,
            },
        ),
        ("patch", f"/students/{student}", {"first_name": "Cambio"}),
        ("delete", f"/students/{student}", None),
        ("post", "/enrollments", {"student_id": student, "course_id": course, "period_id": period}),
        (
            "post",
            "/imports/students/commit",
            {"grade_id": ids["grade"], "section_id": section, "rows": []},
        ),
    ]
    for method, path, data in operations:
        result = client.request(method, path, json=data)
        assert result.status_code == 403, (role, path, result.text)
    result = client.post(
        "/imports/preview",
        files={"file": ("pupils.csv", b"Codigo,Nombres,Apellidos\nX,Alumno,Sintetico\n")},
    )
    assert result.status_code == 403


def test_admin_assignment_makes_new_grade_visible_to_teacher(policy_api):
    client, ids, actors, current = policy_api
    current["user"] = actors["admin"]
    grade = client.post("/academic/grades", json={"name": "2°", "level": "Secundaria"})
    assert grade.status_code == 201
    section = client.post("/academic/sections", json={"grade_id": grade.json()["id"], "name": "A"})
    assert section.status_code == 201
    current["user"] = actors["teacher"]
    assert grade.json()["id"] not in {row["id"] for row in client.get("/academic/grades").json()}
    assert ids["sections"][2] not in {row["id"] for row in client.get("/academic/sections").json()}
    current["user"] = actors["admin"]
    path = f"/courses/{ids['courses'][0]}/assignments"
    assert (
        client.post(
            path, json={"section_id": section.json()["id"], "teacher_name": "Solo nombre"}
        ).status_code
        == 422
    )
    result = client.post(
        path, json={"section_id": section.json()["id"], "teacher_id": str(actors["teacher"].id)}
    )
    assert result.status_code == 201
    current["user"] = actors["teacher"]
    assert grade.json()["id"] in {row["id"] for row in client.get("/academic/grades").json()}
    assert section.json()["id"] in {row["id"] for row in client.get("/academic/sections").json()}
    assert grade.json()["id"] in {
        row["id"] for row in client.get("/academic/catalog").json()["grades"]
    }


def test_teacher_still_imports_grades_for_assigned_students(policy_api):
    client, ids, actors, current = policy_api
    current["user"] = actors["teacher"]
    row = {
        "student_code": "SYN-0",
        "score": 14,
        "evaluation_type": "Cuaderno",
        "evaluation_name": "Importación autorizada",
        "assessment_date": "2026-04-01",
    }
    payload = {"course_id": ids["courses"][0], "period_id": ids["period"], "rows": [row]}
    preview = client.post(
        "/imports/grades/preview",
        files={
            "file": (
                "grades.csv",
                b"student_code,score,assessment_date,evaluation_type\nSYN-0,14,2026-04-01,Cuaderno\n",
            )
        },
    )
    assert preview.status_code == 200
    assert client.post("/imports/grades/review", json=payload).status_code == 200
    result = client.post("/imports/grades/commit", json=payload)
    assert result.status_code == 200, result.text
    assert result.json()["imported"] == 1
    assert client.post("/imports/grades/commit", json=payload).json()["skipped"] == 1


@pytest.mark.parametrize("role", ["admin", "coordinator", "director"])
def test_management_and_academic_area_cannot_change_grades_or_weights(policy_api, role):
    client, ids, actors, current = policy_api
    current["user"] = actors[role]
    records = client.get("/grades").json()
    assert len(records) == 5
    configuration = institutional_template(ids["courses"][0], ids["period"]).document()
    assert client.patch(f"/grades/{records[0]['id']}", json={"score": 1}).status_code == 403
    assert client.delete(f"/grades/{records[0]['id']}").status_code == 403
    assert client.post(
        f"/courses/{ids['courses'][0]}/evaluation-configurations/publish",
        json={"configuration": configuration, "expected_version": 0, "reason": "Cambio"},
    ).status_code == 403
    assert client.post(
        f"/courses/{ids['courses'][0]}/assessment-components",
        json={"name": "Examen", "weight": 2},
    ).status_code == 403
    assert client.post(
        "/imports/grades/preview", files={"file": ("grades.csv", b"student_code,score\nX,15")}
    ).status_code == 403
    assert client.get("/grades").json() == records


def test_assigned_teacher_owns_weights_and_configuration(policy_api, sessions):
    from uuid import UUID

    from sqlalchemy import select

    from app.models.academic import CourseAssignment

    client, ids, actors, current = policy_api
    current["user"] = actors["teacher"]
    course_id = ids["courses"][0]
    configuration = institutional_template(course_id, ids["period"]).document()
    assert client.post(
        f"/courses/{course_id}/evaluation-configurations/publish",
        json={
            "configuration": configuration, "expected_version": 0, "reason": "Criterios del curso",
        },
    ).status_code == 201
    component = client.post(
        f"/courses/{course_id}/assessment-components", json={"name": "Examen", "weight": 2}
    )
    assert component.status_code == 201
    component_id = component.json()["id"]
    assert client.patch(
        f"/courses/{course_id}/assessment-components/{component_id}", json={"weight": 3}
    ).json()["weight"] == 3
    with sessions() as db:
        db.scalar(select(CourseAssignment).where(
            CourseAssignment.course_id == UUID(course_id)
        )).teacher_id = None
        db.commit()
    assert client.patch(
        f"/courses/{course_id}/assessment-components/{component_id}", json={"weight": 4}
    ).status_code == 403
    assert client.post(
        f"/courses/{course_id}/evaluation-configurations/publish",
        json={"configuration": configuration, "expected_version": 1, "reason": "Cambio"},
    ).status_code == 403


@pytest.mark.parametrize("role", ["coordinator", "director"])
def test_academic_area_follows_all_classrooms_without_teaching_assignment(policy_api, role):
    client, ids, actors, current = policy_api
    current["user"] = actors[role]
    assert len(client.get("/students").json()) == 3
    assert client.get("/academic/catalog", params={
        "grade_id": ids["grade"], "section_id": ids["sections"][2],
    }).json()["students"][0]["id"] == ids["students"][2]
    item = client.post("/follow-up", json={
        "student_id": ids["students"][2], "action": "Reunión de acompañamiento",
    })
    assert item.status_code == 201
    assert item.json()["recorded_by_id"] == str(actors[role].id)
    current["user"] = actors["teacher"]
    assert client.post("/follow-up", json={
        "student_id": ids["students"][0], "action": "Intento de creación",
    }).status_code == 403
