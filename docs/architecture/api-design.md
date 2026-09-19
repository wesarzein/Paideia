# Diseno de API

Version base: `/api/v1`.

Endpoints MVP:

```http
GET /api/v1/health
GET /api/v1/students
GET /api/v1/students/summary
POST /api/v1/students
GET /api/v1/students/{student_id}
PATCH /api/v1/students/{student_id}
DELETE /api/v1/students/{student_id}
```

Respuesta:

```json
{ "status": "ok" }
```

Los estudiantes se persisten en PostgreSQL mediante SQLAlchemy y Alembic. `GET /api/v1/students` admite los filtros opcionales `search` y `status`; `POST` requiere `student_code`, `first_name` y `last_name`.

La API usa REST, JSON y OpenAPI mediante FastAPI. Las interfaces de IA y BI quedan reservadas para siguientes iteraciones; por ahora el frontend solo mantiene sus rutas de navegación.
