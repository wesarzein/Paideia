# Diseno de API

Version base: `/api/v1`.

Este listado describe el MVP inicial y no sustituye el OpenAPI actual. El código escolar ahora se genera en el servidor a partir de grado/sección; no tomar la descripción antigua de campos obligatorios como contrato vigente. Consultar la [auditoría académica de Fase 4A](../academic/auditoria-fase4a.md) para los flujos verificados y sus limitaciones.

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
