# Diseno de base de datos

## Tablas iniciales

- `users`: usuarios del sistema con `password_hash`.
- `roles`: roles institucionales.
- `students`: estudiantes.
- `academic_periods`: periodos academicos.
- `grades`: grados.
- `sections`: secciones asociadas a grados.
- `courses`: cursos.

Desde Fase 3 el backend inicia sin ejecutar migraciones: Alembic se aplica como operación explícita y revisada. La [guía de entornos](phase3-environments.md) describe ese procedimiento. Este documento conserva el diseño inicial; el inventario académico vigente se registra en la [auditoría de Fase 4A](../academic/auditoria-fase4a.md), sin dar por implementadas las tablas previstas.

## Modelo previsto

`permissions`, `enrollments`, `evaluations`, `grades_records`, `attendance`, `academic_follow_up`, `risk_predictions`, `interventions`, `imports`, `import_errors` y `audit_logs` se agregaran por sprint.

## Criterios

UUID como identificador interno, claves foraneas, 3FN, timestamps timezone-aware y datos en UTF-8.
